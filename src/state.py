#!/usr/bin/env python3
"""What the bot already knows, so it does not tell you twice.

One JSON file, `~/.config/berlin-flat-bot/state.json`. Small enough to read,
and worth reading when something behaves oddly.

The important idea here is that **a flat is not a link**. The same flat is
posted on ImmoScout, on Kleinanzeigen and on the landlord's own site, often
with different wording and always with different URLs, and treating those as
three finds means three messages for one flat. Worse, a listing rejected by
hand under one URL comes straight back under another.

So identity is the flat itself: postcode, street, house number and size. That
is not perfect, since one building can have several flats of the same size, but
adding the size makes collisions rare, and the failure mode is quiet rather
than noisy: a duplicate shows up as a line saying "already sent" instead of a
second card.
"""
import json, os, pathlib, re, time

STATE = pathlib.Path(os.path.expanduser("~/.config/berlin-flat-bot/state.json"))

_EMPTY = {"seen": [], "sent": [], "rejected": [], "applied": []}


def load():
    try:
        d = json.loads(STATE.read_text())
    except Exception:
        return dict(_EMPTY)
    for k in _EMPTY:
        d.setdefault(k, [])
    return d


def save(d):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Keep the seen list from growing without end. Everything else is small.
    d["seen"] = d["seen"][-4000:]
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    tmp.replace(STATE)


# ────────────────────────────── identity ────────────────────────────────────

def _street(address):
    """Street and house number, normalised. German spelling varies a lot."""
    a = (address or "").lower()
    a = a.replace("ß", "ss")
    a = re.sub(r"(str|strasse|straße)\b\.?", "str", a)
    a = re.sub(r"[.,]", " ", a)
    m = re.search(r"([a-zäöü\- ]+str|[a-zäöü\-]+(?:weg|allee|damm|platz|ufer|ring|gasse|chaussee))"
                  r"\s*(\d+\s*[a-z]?)?", a)
    if not m:
        return ""
    return (m.group(1).strip() + " " + (m.group(2) or "").replace(" ", "")).strip()


def flat_key(address, size=None):
    """A stable identity for one flat, independent of which portal listed it."""
    plz = (re.search(r"\b(1[0-9]{4})\b", address or "") or [None, ""])[1] \
        if re.search(r"\b1[0-9]{4}\b", address or "") else ""
    st = _street(address)
    sz = f"{round(float(size)):d}" if size else ""
    key = "|".join(x for x in (plz, st, sz) if x)
    return key or None


def listing_id(row):
    """Portal id where there is one, so the same advert is recognised after an
    edit. Portals change the slug in a URL freely and the number never."""
    link = row.get("link") or ""
    for rx, pre in ((r"kleinanzeigen\.de/.*?/(\d{6,})(?:[-/]|$)", "ka"),
                    (r"immobilienscout24\.de/(?:expose/)?(\d{6,})", "is24"),
                    (r"immowelt\.de/expose/([a-z0-9]+)", "iw")):
        m = re.search(rx, link, re.I)
        if m:
            return f"{pre}:{m.group(1)}"
    return (row.get("id") or link or "").strip().rstrip("/")


# ─────────────────────────────── queries ────────────────────────────────────

def seen(d, row):
    return listing_id(row) in set(d["seen"])


def sent_before(d, row):
    """The earlier record for this flat, or None. Matches across portals."""
    k = flat_key(row.get("address"), row.get("size"))
    if not k:
        return None
    return next((s for s in d["sent"] if s.get("key") == k), None)


def rejected(d, row):
    """True when this flat was turned down by hand, under any of its URLs."""
    k = flat_key(row.get("address"), row.get("size"))
    ids = set(d["rejected"])
    return listing_id(row) in ids or (k and k in ids)


def applied(d, row):
    """True when an application already went out for this flat.

    Written by the mail watcher from the portals' own confirmations. Without
    it a flat can arrive as a fresh card ten minutes after you applied to it,
    which has happened and is disorienting rather than merely redundant.
    """
    k = flat_key(row.get("address"), row.get("size"))
    recs = d["applied"]
    return any(a.get("key") == k or a.get("id") == listing_id(row) for a in recs)


def remember_seen(d, row):
    i = listing_id(row)
    if i and i not in d["seen"]:
        d["seen"].append(i)


def remember_sent(d, row, score=None):
    k = flat_key(row.get("address"), row.get("size"))
    rec = next((s for s in d["sent"] if s.get("key") == k), None) if k else None
    link = row.get("link")
    if rec:
        if link and link not in rec["links"]:
            rec["links"].append(link)
        return rec
    rec = {"key": k, "links": [link] if link else [], "score": score,
           "addr": row.get("address"), "at": int(time.time())}
    d["sent"].append(rec)
    return rec


def reject(d, row):
    """Turn a flat down by hand. Silences it on every portal it appears on."""
    for x in (listing_id(row), flat_key(row.get("address"), row.get("size"))):
        if x and x not in d["rejected"]:
            d["rejected"].append(x)
