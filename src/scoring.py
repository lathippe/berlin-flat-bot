#!/usr/bin/env python3
"""Score a listing out of 100.

The score never decides anything on its own. Gates decide; the score only
orders what survived them, and sets the floor below which something that
technically passed is not worth a message.

Normalisation matters and is easy to get wrong. The base components add up to
the weights in the profile, and bonuses sit on top. If you only divide by the
base, half the shortlist comes out at 100/100 and you cannot tell those flats
apart, which is exactly what happened in the original before this was fixed.
So the divisor is everything achievable, and 100 goes only to a flat where
every single thing landed.
"""
import math, re

import listings as L


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in (patterns or []))


def _band(value, table):
    """First (limit, points) pair the value falls under."""
    for lim, pts in table:
        if value is not None and value <= lim:
            return pts
    return 0


def score(listing, prof, tier=None, anchor_minutes=None, nearby_hits=None):
    """(0-100, flags, parts).

    listing        dict: title, description, address, size, rooms, kalt, warm,
                   dist_km (straight line to the centre)
    tier           'rail' | 'tram' | 'bus' | None, from the transit module
    anchor_minutes {anchor id: door-to-door minutes or None}
    nearby_hits    output of places.measure(), or None
    """
    import profile as P

    w     = prof["weights"]
    text  = ((listing.get("title") or "") + " " + (listing.get("description") or "")).lower()
    addr  = (listing.get("address") or "").lower()
    size  = listing.get("size") or 0
    kalt  = listing.get("kalt") or 0
    warm, _real = P.warm_of(kalt, listing.get("warm"), prof)
    areas = prof["areas"]

    s, flags, parts = 0.0, [], {}
    earned_max = 0.0

    def add(name, pts, cap):
        nonlocal s, earned_max
        s += pts
        earned_max += cap
        parts[name] = round(pts, 1)

    # ── area ────────────────────────────────────────────────────────────────
    # Favourite is the full weight, "ok" is a bit under half. Everything else
    # scores nothing here rather than being penalised: a neighbourhood nobody
    # named is unknown, not bad.
    if _any(areas.get("favourite"), addr):
        add("area", w["area"], w["area"])
    elif _any(areas.get("ok"), addr):
        add("area", w["area"] * 0.45, w["area"])
    else:
        add("area", 0, w["area"])

    # ── distance to the centre ──────────────────────────────────────────────
    d = listing.get("dist_km")
    add("centre", _band(d, [(3, w["centre"]), (5, w["centre"]),
                            (6.5, w["centre"] * 0.875), (8, w["centre"] * 0.5),
                            (10, w["centre"] * 0.25)]), w["centre"])

    # ── transit ─────────────────────────────────────────────────────────────
    # Tram is worth about half of rail rather than nothing: slower and it
    # stops in traffic, but it is still a rail-shaped way to cross the city.
    add("transit", {"rail": w["transit"], "tram": w["transit"] * 0.48}.get(tier, 0),
        w["transit"])

    # ── price per m2 ────────────────────────────────────────────────────────
    lo, hi = prof["market_ppm"]
    ppm = (kalt / size) if size else None
    if ppm is None:
        add("price_per_sqm", 0, w["price_per_sqm"])
    elif ppm < lo * 0.83:
        add("price_per_sqm", w["price_per_sqm"] * 0.4, w["price_per_sqm"])
        flags.append("suspiciously cheap")
    elif ppm <= lo:
        add("price_per_sqm", w["price_per_sqm"], w["price_per_sqm"])
    elif ppm <= hi:
        add("price_per_sqm", w["price_per_sqm"] * 0.87, w["price_per_sqm"])
    elif ppm <= hi * 1.18:
        add("price_per_sqm", w["price_per_sqm"] * 0.53, w["price_per_sqm"])
    else:
        add("price_per_sqm", w["price_per_sqm"] * 0.13, w["price_per_sqm"])
        flags.append("expensive per m²")

    # ── the absolute rent ───────────────────────────────────────────────────
    # Scored separately from price per m2 on purpose. On its own, price per m2
    # rewards taking more space at a higher rent, which is backwards: the
    # point is to spend less, not to buy square metres efficiently.
    b = prof.get("budget") or {}
    target, cap = b.get("target_warm"), b.get("max_warm")
    if warm and cap:
        t = target or cap
        add("rent", _band(warm, [(t * 0.8, w["rent"]), (t, w["rent"] * 0.9),
                                 (cap, w["rent"] * 0.8),
                                 (b.get("stretch_warm") or cap, w["rent"] * 0.2)]),
            w["rent"])
        if target and warm > target:
            flags.append(f"{warm - target:.0f} € above your comfortable level")
    else:
        add("rent", 0, w["rent"])

    # ── size ────────────────────────────────────────────────────────────────
    # A band with a plateau, not a peak, and not "bigger is better". Above the
    # band every extra m² is rent, heating and cleaning for space nobody asked
    # for, so it scores less, not more.
    sweet = prof["home"].get("sweet_size") or [45, 65]
    floor = (prof["home"].get("min_size_sqm") or sweet[0])
    if not size:
        add("size", 0, w["size"])
    elif sweet[0] <= size <= sweet[1]:
        add("size", w["size"], w["size"])
    elif floor <= size < sweet[0]:
        add("size", w["size"] * 0.8, w["size"])
    elif size < floor:
        add("size", w["size"] * 0.6, w["size"]); flags.append(f"{size:.0f} m², tight")
    elif size <= sweet[1] * 1.15:
        add("size", w["size"] * 0.5, w["size"]); flags.append(f"{size:.0f} m², more than needed")
    else:
        add("size", w["size"] * 0.2, w["size"])
        flags.append(f"{size:.0f} m², space to heat and clean")

    # ── rooms ───────────────────────────────────────────────────────────────
    need = prof["home"].get("min_rooms") or 2
    add("rooms", w["rooms"] if (listing.get("rooms") or 0) >= need else w["rooms"] * 0.4,
        w["rooms"])

    # ── anchors ─────────────────────────────────────────────────────────────
    for a in prof.get("anchors", []):
        aw = float(a.get("weight") or 0)
        if not aw:
            continue
        mins = (anchor_minutes or {}).get(a["id"])
        limit = a.get("max_minutes") or 45
        if mins is None:
            add(f"anchor:{a['id']}", 0, aw)
        else:
            # Full marks at a third of the limit, nothing at the limit itself.
            frac = max(0.0, min(1.0, (limit - mins) / max(1.0, limit * 0.67)))
            add(f"anchor:{a['id']}", aw * frac, aw)

    # ── nearby ──────────────────────────────────────────────────────────────
    if nearby_hits:
        import places
        pts, _ = places.score(nearby_hits)
        cap = sum(float(n.get("weight") or 0) for n in prof.get("nearby", []))
        add("nearby", pts, cap)

    # ── features ────────────────────────────────────────────────────────────
    fp, fflags = L.features(text, wanted=prof["home"].get("wants"),
                            avoided=prof["home"].get("deal_breakers"))
    s += fp
    earned_max += sum(abs(float(L.FEATURES[n.lower()]["points"]))
                      for n in (prof["home"].get("wants") or [])
                      if n.lower() in L.FEATURES)
    parts["features"] = round(fp, 1)
    flags += fflags

    # ── areas you would rather not ──────────────────────────────────────────
    if _any(areas.get("low_priority"), addr):
        s -= w["area"] * 0.4
        flags.append("LOW PRIORITY AREA")

    if earned_max <= 0:
        return 0, flags, parts
    return max(0, min(round(s / earned_max * 100), 100)), flags, parts


def passes(value, prof):
    return value >= (prof.get("min_score") or 52)
