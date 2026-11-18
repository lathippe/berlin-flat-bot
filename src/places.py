#!/usr/bin/env python3
"""Answer "what is near this flat", for every entry in profile.nearby.

One function matters to the rest of the bot:

    measure(lat, lng, profile)  ->  [Hit, ...]

Each Hit says how many matching places sit inside the radius, how far the
closest one is, and names a couple of them. `line()` turns a Hit into the
string that goes on the Telegram card.

Three kinds of source, and they are not equally trustworthy. The card says
which one answered, because "four nurseries within 900 m" from the official
register and "four Indian restaurants" from OpenStreetMap are different
classes of claim:

    berlin-kita    official Berlin nursery register, 2905 entries, local file
    berlin-school  official Berlin school register, 930 entries, local file
    overpass       OpenStreetMap, live query, whatever the public map knows
    manual         recorded in the profile, nothing wired up, never measured

docs/nearby.md explains what each one can and cannot tell you.
"""
import hashlib, json, math, os, pathlib, time, urllib.parse, urllib.request

HERE  = pathlib.Path(__file__).resolve().parent
DATA  = HERE.parent / "data"
CACHE = pathlib.Path(os.path.expanduser("~/.cache/berlin-flat-bot"))
UA    = "berlin-flat-bot/1.0"

# Public Overpass instances. The main one returns 504 under load often enough
# that a single-endpoint client is not usable: during testing it failed roughly
# half of all requests. Tried in order, first answer wins.
#
# Timeouts are deliberately short. Three mirrors at 75 seconds each meant a
# single uncached address could sit there for four minutes before giving up,
# which is useless in a race where the point is to answer fast. 30 seconds a
# mirror, 25 server-side, and anything slower than that is treated as down.
# The cache below is what makes this cheap in the normal case.
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
CACHE_DAYS = 30          # POIs do not move. Nurseries do not open weekly.

_LOCAL = {}


# ───────────────────────────────── geometry ─────────────────────────────────

def metres(a_lat, a_lng, b_lat, b_lng):
    R, p = 6371000.0, math.pi / 180
    h = (math.sin((b_lat - a_lat) * p / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lng - a_lng) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


# ─────────────────────────────── local registers ────────────────────────────

def _load(fname):
    if fname not in _LOCAL:
        f = DATA / fname
        if not f.exists():
            raise FileNotFoundError(
                f"{f} is missing. Run `python3 data/fetch.py` once to download it.")
        _LOCAL[fname] = json.loads(f.read_text())
    return _LOCAL[fname]


def _local_hits(fname, lat, lng, radius, query):
    """Rows of a local register inside the radius, nearest first.

    `query` filters on the record's own fields, e.g. {"kind": "Grundschule"}.
    The value is treated as a regex so one entry can ask for
    "Gymnasium|Gemeinschaftsschule" without listing every school type.
    """
    import re
    out = []
    for r in _load(fname):
        if query:
            ok = True
            for k, want in query.items():
                have = str(r.get(k) or r.get({"type": "kind"}.get(k, k)) or "")
                if not re.search(str(want), have, re.I):
                    ok = False
                    break
            if not ok:
                continue
        d = metres(lat, lng, r["lat"], r["lng"])
        if d <= radius:
            out.append((d, r.get("name") or "?"))
    return sorted(out)


# ────────────────────────────────── overpass ────────────────────────────────

def _cache_path(key):
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")


def _overpass(clauses, lat, lng, radius):
    """Count OSM objects matching any clause within the radius.

    `clauses` is one or more Overpass selectors separated by ';', each without
    the (around:) part, e.g. 'nwr["leisure"="playground"]'. The area filter is
    appended here so a profile cannot forget it and query the whole planet.

    Coordinates are rounded to three decimals (about 80 m) before they become
    the cache key: two listings in the same building must not each cost a
    network round trip.
    """
    parts = [c.strip() for c in str(clauses).split(";") if c.strip()]
    body = "".join(f"{c}(around:{radius},{lat:.5f},{lng:.5f});" for c in parts)
    q = f"[out:json][timeout:25];({body});out center;"
    key = f"{lat:.3f},{lng:.3f}|{radius}|{clauses}"
    cf = _cache_path(key)
    if cf.exists() and time.time() - cf.stat().st_mtime < CACHE_DAYS * 86400:
        try:
            return json.loads(cf.read_text())
        except Exception:
            pass

    last = None
    for url in OVERPASS:
        try:
            data = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(url, data, {"User-Agent": UA})
            r = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as exc:
            last = exc
            continue
        hits = []
        for e in r.get("elements", []):
            c = e.get("center") or e
            if c.get("lat") is None:
                continue
            hits.append((metres(lat, lng, c["lat"], c["lon"]),
                         (e.get("tags") or {}).get("name") or "?"))
        hits.sort()
        cf.write_text(json.dumps(hits))
        return hits
    # Every mirror refused. Return None, not an empty list: "the map says there
    # is nothing here" and "nobody answered the phone" must not look the same
    # on the card, or a network outage silently reads as a bad neighbourhood.
    print(f"  overpass unavailable ({type(last).__name__ if last else '?'})")
    return None


# ──────────────────────────────── public API ────────────────────────────────

class Hit(dict):
    """count, nearest (metres or None), names, ok (False = could not measure)."""
    __getattr__ = dict.get


def measure(lat, lng, profile):
    out = []
    for n in profile.get("nearby", []):
        src, radius = n.get("source"), int(n.get("radius_m") or 1000)
        hits = None
        if src == "berlin-kita":
            hits = _local_hits("kita.json", lat, lng, radius, n.get("query"))
        elif src == "berlin-school":
            hits = _local_hits("schools.json", lat, lng, radius, n.get("query"))
        elif src == "overpass":
            hits = _overpass(n.get("query"), lat, lng, radius)
        elif src == "manual":
            out.append(Hit(spec=n, ok=False, why="no data source wired up"))
            continue
        if hits is None:
            out.append(Hit(spec=n, ok=False, why="source unavailable"))
            continue
        out.append(Hit(spec=n, ok=True, count=len(hits),
                       nearest=round(hits[0][0]) if hits else None,
                       names=[nm for _, nm in hits[:3]]))
    return out


def gate(hits):
    """Reject reasons from entries that set min_count. Empty list means pass.

    An entry that could not be measured never rejects. A flat is not dropped
    because a server was down.
    """
    bad = []
    for h in hits:
        need = (h.spec or {}).get("min_count")
        if need and h.get("ok") and (h.get("count") or 0) < need:
            bad.append(f"{h.spec['label']}: {h.get('count', 0)} within "
                       f"{h.spec['radius_m']} m, wanted {need}")
    return bad


def score(hits):
    """Points earned by the nearby entries, and the flags to show.

    want=any   full weight for the first one found, nothing extra after that
    want=many  full weight at five or more, pro rata below
    want=none  full weight when there are none, zero as soon as there is one
    """
    pts, flags = 0.0, []
    for h in hits:
        s = h.spec or {}
        w = float(s.get("weight") or 0)
        if not h.get("ok") or not w:
            continue
        c = h.get("count") or 0
        want = s.get("want") or "any"
        if want == "many":
            pts += w * min(c, 5) / 5.0
        elif want == "none":
            pts += w if c == 0 else 0.0
        else:
            pts += w if c else 0.0
    return pts, flags


def line(h):
    """One card line. Says which register answered when it is an official one.

    An entry can set `show_label: false`, and then the line leads with the
    places themselves instead of the category name. That exists for the
    community entries: somebody who asked to be near their own community does
    not need every message to announce the category back at them. They know
    why they asked. What they cannot get anywhere else is which temple and
    which grocer, and how far.
    """
    s = h.spec or {}
    label = s.get("label") or s.get("id")
    show_label = s.get("show_label", True)
    radius, near = s.get("radius_m"), h.get("nearest")
    names = ", ".join(n for n in (h.get("names") or []) if n and n != "?")
    src = {"berlin-kita": " (official register)",
           "berlin-school": " (official register)"}.get(s.get("source"), "")

    if not h.get("ok"):
        # With the label hidden there is nothing left to identify the line, and
        # "· not measured (source unavailable)" on its own tells the reader
        # nothing at all. Drop it. A missing line is better than a line that
        # cannot be understood.
        return (f"· {label}: not measured ({h.get('why')})" if show_label else None)
    c = h.get("count") or 0
    if not c:
        return (f"· {label}: none within {radius} m{src}" if show_label
                else f"· nothing within {radius} m")
    if not show_label:
        tail = f"{c} within {_km(radius)}" + (f", closest {near} m" if near is not None else "")
        return f"· {names} — {tail}" if names else f"· {tail}"
    head = f"· {label}: {c} within {radius} m"
    if near is not None:
        head += f", closest {near} m"
    return head + src + (f" — {names}" if names else "")


def _km(m):
    return f"{m/1000:g} km" if m and m >= 1000 else f"{m} m"


if __name__ == "__main__":
    import sys
    lat, lng = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (52.4886, 13.4253)
    prof = json.loads((HERE.parent / "profile.json").read_text())
    hs = measure(lat, lng, prof)
    print(f"{lat}, {lng}")
    for h in hs:
        print(" ", line(h))
    print(f"\n  nearby points: {score(hs)[0]:.1f}")
    for b in gate(hs):
        print("  REJECT:", b)
