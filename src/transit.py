#!/usr/bin/env python3
"""How long it takes to get out of this flat and to the places you care about.

Two questions, and they are not the same one:

  tier(lat, lng)        What is at the door. Rail, tram, or only a bus.
  minutes(lat, lng, …)  Door to door to each of your anchors.

Routing comes from transitous.org, a free MOTIS instance with German timetable
data. No key needed. Be reasonable with it; everything here is cached on disk.

Three decisions worth knowing about, each of which cost a wrong answer first:

* **The clock is pinned to Tuesday 9am.** A scheduled run at 3am would
  otherwise measure against the night timetable and throw away perfectly good
  addresses, or flatter them.

* **Bus legs are excluded when the profile does not count buses.** Routing by
  "fastest" means routing by bus, because from a bus-shaped neighbourhood the
  fastest trip starts with a bus. One address measured 35 minutes that way and
  really took 45, because every fast option began with a bus and the nearest
  rail was a 16 minute walk. If buses do not count for you, they must not count
  when measuring either.

* **Walking time is routed, not estimated.** A stop 975 m away in a straight
  line was 1 153 m and 16 minutes on foot, and the straight line put it inside
  the "metro at the door" radius. Below 300 m the estimate is used; past that
  the walk is always routed, because in Neukölln the detour factor reaches 75%.
"""
import json, os, math, pathlib, time, urllib.parse, urllib.request
from datetime import datetime, timedelta

MOTIS = "https://api.transitous.org/api/v1"
CACHE = pathlib.Path(os.path.expanduser("~/.cache/berlin-flat-bot/transit.json"))
UA    = "berlin-flat-bot/1.0"

# MOTIS uses two different mode vocabularies at two endpoints, and this is not
# a typo: reverse-geocode reports SUBURBAN at a stop while stoptimes reports
# METRO for the same services. Filtering on one set alone dropped the S-Bahn at
# Gesundbrunnen entirely, leaving a station with S1, S2, S25, S41, S42 and U8
# looking like it only had the U8.
RAIL_MODES = {"SUBWAY", "METRO", "SUBURBAN", "RAIL", "REGIONAL_RAIL",
              "HIGHSPEED_RAIL", "NIGHT_RAIL"}
TRAM_MODES = {"TRAM"}
NOBUS      = "SUBWAY,METRO,TRAM,RAIL,REGIONAL_RAIL"

PRE_WALK  = 1800     # seconds MOTIS may walk to the first stop. The default is
                     # too low: where the station is a long walk away it finds
                     # no rail route at all, and the address then looks like
                     # "no route" rather than "far on foot".
WALK_KMH  = 4.3
STOP_NEAR = 300      # metres below which the straight-line estimate is kept

_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE.read_text())
        except Exception:
            _cache = {}
    return _cache


def save():
    c = _load()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c))


def metres(a_lat, a_lng, b_lat, b_lng):
    R, p = 6371000.0, math.pi / 180
    h = (math.sin((b_lat - a_lat) * p / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lng - a_lng) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def _next_tuesday_9am():
    d = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    return d + timedelta(days=(1 - d.weekday()) % 7 or 7)


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def plan(lat, lng, dest, allow_bus=False):
    """(minutes, first-leg modes, walking minutes to the first stop, stop name).

    All None when there is no route at all.
    """
    key = f"{lat:.4f},{lng:.4f}>{dest[0]:.4f},{dest[1]:.4f}{'' if allow_bus else 'r'}"
    c = _load()
    if key in c:
        return tuple(c[key])

    when = _next_tuesday_9am().strftime("%Y-%m-%dT%H:%M:00") + "Z"
    modes = ("transitModes=TRANSIT" if allow_bus else
             f"transitModes={NOBUS}&maxPreTransitTime={PRE_WALK}"
             f"&maxPostTransitTime={PRE_WALK}")
    url = (f"{MOTIS}/plan?fromPlace={lat},{lng}&toPlace={dest[0]},{dest[1]}"
           f"&{modes}&numItineraries=4&time={when}")
    try:
        j = _get(url)
    except Exception:
        return (None, [], None, None)          # not cached: a timeout is not an answer

    its = sorted(j.get("itineraries") or [], key=lambda x: x.get("duration", 1e9))
    if not its:
        res = (None, [], None, None)
    else:
        legs  = its[0].get("legs") or []
        first = [l.get("mode") for l in legs if l.get("mode") not in ("WALK", "BIKE", "CAR")]
        walk  = round(legs[0]["duration"] / 60) if legs and legs[0].get("mode") == "WALK" else 0
        board = next((l.get("from", {}).get("name") for l in legs
                      if l.get("mode") not in ("WALK", "BIKE", "CAR")), None)
        res = (round(its[0]["duration"] / 60), first, walk, board)
    c[key] = list(res)
    return res


def minutes_to_anchors(lat, lng, prof):
    """{anchor id: door-to-door minutes or None}, honouring the profile's modes."""
    allow_bus = "bus" in (prof.get("transit") or {}).get("modes", [])
    out = {}
    for a in prof.get("anchors", []):
        dest = (a["lat"], a["lng"])
        m, _f, _w, _b = plan(lat, lng, dest, allow_bus=allow_bus)
        if m is None:
            # A flat 180 m from the office is not "unreachable". MOTIS does not
            # plan a trip that short, and dropping those addresses was a real
            # bug: the flat nearest the office scored worst.
            d = metres(lat, lng, *dest)
            if d <= 2000:
                m = max(1, round(d / 1000 / WALK_KMH * 60))
            elif plan(lat, lng, dest, allow_bus=True)[0] is not None:
                # There is a route, just not one you would take. 999 makes it
                # fail on time rather than vanish into "no route", which is
                # where genuine network errors live.
                m = 999
        out[a["id"]] = m
    return out


def tier(lat, lng, prof):
    """('rail' | 'tram' | 'bus' | None, label for the card).

    Decided by the first leg of a real journey rather than by what is near in a
    straight line, because a station across a canal is not near.
    """
    modes_ok = set((prof.get("transit") or {}).get("modes") or [])
    max_walk = (prof.get("transit") or {}).get("max_walk_min") or 12

    # Route to the centre of town purely to see what you would board first.
    _m, first, walk, board = plan(lat, lng, (52.5200, 13.4050), allow_bus=False)
    kind = None
    if first:
        if set(first) & RAIL_MODES:
            kind = "rail"
        elif set(first) & TRAM_MODES:
            kind = "tram"
    if kind is None or (walk is not None and walk > max_walk):
        if plan(lat, lng, (52.5200, 13.4050), allow_bus=True)[0] is not None:
            kind = "bus"
    if kind and kind not in modes_ok and kind != "bus":
        kind = None

    icon = {"rail": "🚇", "tram": "🚊", "bus": "🚌"}.get(kind, "🚉")
    if kind == "bus":
        return "bus", f"{icon} bus only"
    if board and walk is not None:
        name = board.replace("(Berlin)", "").replace("Berlin,", "").strip(" ,")
        return kind, f"{icon} {name} · {walk} min walk"
    return kind, f"{icon} {'no route found' if kind is None else kind}"
