#!/usr/bin/env python3
"""Decide about one listing, in order, cheapest check first.

    verdict, card_text, info = process(row, prof, st)

`verdict` is None when the listing should be sent, otherwise a short reason it
was not. The reasons are counted and printed at the end of a run, which is how
you find out that a gate is too tight: a hundred listings a day dying on
"outside your areas" means the area list is wrong, and without the tally it
just looks like a quiet market.

Two rules hold throughout:

* **Order is by cost.** Text matching is free, routing is a network call, and
  counting nurseries is several. A listing that fails on its title must never
  reach the router.

* **A check that cannot run does not reject.** If the router times out or
  Overpass is down, the listing goes out with the line marked "not measured".
  Silence caused by an outage is the one failure nobody notices, because it is
  indistinguishable from a market with nothing in it.
"""
import re

import listings as L, places, profile as P, scoring, state, transit


def _text(row):
    return ((row.get("title") or "") + " " + (row.get("description") or "")).lower()


def _hits(patterns, haystack):
    return any(re.search(p, haystack, re.I) for p in (patterns or []))


def process(row, prof, st, measure_nearby=True):
    """(reason or None, context dict). The context carries whatever was
    computed, so the caller can render a card without redoing the work.

    Every rejection also sets `info["kind"]`, a stable category. The per-listing
    reason says "62 m², under your minimum" because that is what you want to
    read next to an address, but a run tallied on those strings splits one
    gate across forty lines, one per size, and the tally stops answering the
    only question it exists to answer: which gate is throwing everything away.
    """
    info = {}

    def no(kind, detail):
        info["kind"] = kind
        return detail, info

    text = _text(row)
    addr = (row.get("address") or "").lower()
    home = prof.get("home") or {}
    areas = prof.get("areas") or {}

    # ── free: what we already know ──────────────────────────────────────────
    if state.rejected(st, row):
        return no("turned down by hand", "turned down by hand")
    if state.applied(st, row):
        return no("already applied", "already applied")
    prev = state.sent_before(st, row)
    if prev:
        info["duplicate_of"] = prev
        return no("already sent", "already sent")

    # ── free: what the text says ────────────────────────────────────────────
    gates = L.hard_hits(text, row.get("title"),
                        gate_pets=bool((prof.get("person") or {}).get("pets")))
    if gates:
        g = gates[0]
        return no(L.LABELS.get(g, g), L.LABELS.get(g, g))
    if L.is_request(text):
        return no("a request, not an offer", "a request, not an offer")
    if _hits([re.escape(d) for d in home.get("deal_breakers") or []], text):
        return no("your deal-breaker", "your deal-breaker")

    # ── free: numbers ───────────────────────────────────────────────────────
    size, rooms = row.get("size") or 0, row.get("rooms") or 0
    if home.get("min_size_sqm") and size and size < home["min_size_sqm"]:
        return no("under your minimum size", f"{size:.0f} m², under your minimum")
    if home.get("min_rooms") and rooms and rooms < home["min_rooms"]:
        return no("under your minimum rooms", f"{rooms:g} rooms, under your minimum")

    warm, warm_real = P.warm_of(row.get("price"), row.get("warm"), prof)
    info["warm"], info["warm_real"] = warm, warm_real
    # Checked before the score exists, so only the absolute ceiling can apply
    # here. The stretch band is re-checked once there is a score.
    if P.over_budget(warm, prof):
        return no("over your rent ceiling", f"{warm:.0f} € warm, over your ceiling")

    # ── free: where ─────────────────────────────────────────────────────────
    if _hits(areas.get("never"), addr):
        return no("in an area you ruled out", "in an area you ruled out")

    lat, lng = row.get("latitude"), row.get("longitude")
    if lat is None or lng is None:
        return no("no coordinates", "no coordinates")
    dist = transit.metres(lat, lng, 52.5200, 13.4050) / 1000
    info["dist_km"] = round(dist, 1)
    if areas.get("max_km_center") and dist > areas["max_km_center"]:
        return no("too far from the centre", f"{dist:.0f} km from the centre")

    # ── costs a network call: how you get out, and how far to your places ───
    tier, tlabel = transit.tier(lat, lng, prof)
    info["tier"], info["transit"] = tier, tlabel
    modes = set((prof.get("transit") or {}).get("modes") or [])
    if tier is None:
        return no("no route found", "no route found")
    if tier == "bus" and "bus" not in modes:
        return no("bus only", "bus only")

    mins = transit.minutes_to_anchors(lat, lng, prof)
    info["anchors"] = mins
    for a in prof.get("anchors", []):
        lim, got = a.get("max_minutes"), mins.get(a["id"])
        if lim and got is not None and got > lim:
            return no(f"too far from {a['label']}", f"{got} min to {a['label']}")

    # ── costs several network calls: what is nearby ─────────────────────────
    if measure_nearby:
        hits = places.measure(lat, lng, prof)
        info["nearby"] = hits
        bad = places.gate(hits)
        if bad:
            return no("not enough nearby", bad[0])

    # ── the score ───────────────────────────────────────────────────────────
    listing = dict(title=row.get("title"), description=row.get("description"),
                   address=row.get("address"), size=size, rooms=rooms,
                   kalt=row.get("price"), warm=warm, dist_km=info["dist_km"])
    sc, flags, parts = scoring.score(listing, prof, tier=tier, anchor_minutes=mins,
                                     nearby_hits=info.get("nearby"))
    info.update(score=sc, flags=flags, parts=parts, listing=listing)

    if P.over_budget(warm, prof, score=sc):
        return no("over ceiling and not good enough", f"{warm:.0f} € warm and only scores {sc}")
    floor = prof.get("min_score") or 52
    if sc < floor:
        return no("scores below your floor", f"scores {sc}")
    return None, info
