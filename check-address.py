#!/usr/bin/env python3
"""Run one address through everything the bot knows.

    python3 check-address.py "Boxhagener Straße 40, Berlin"
    python3 check-address.py "Boxhagener Str. 40" --size 92 --rooms 4 --warm 1540

No tokens, no Fredy, no mailbox. It geocodes the address, routes to each place
you named, counts what you asked to have nearby, reads the neighbourhood
statistics, and prints the card you would have been sent.

This is useful on its own, before any of the delivery machinery exists: when
you find a flat yourself and want to know what the area is actually like, or
when you want to see whether your profile agrees with you about somewhere you
already know. If it disagrees, the profile is wrong, and that is worth finding
out on an address you can judge rather than on one you cannot.

With the rent and size given it also scores the flat. Without them it stops
after the location, which is the half that does not depend on the listing.
"""
import argparse, json, pathlib, sys, time, urllib.parse, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))
import profile as P, transit, places, kiez, card, scoring, listings as L

UA = "berlin-flat-bot/1.0 (address check)"


def geocode(q):
    if "berlin" not in q.lower():
        q += ", Berlin"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "de"})
    r = json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=25))
    time.sleep(1.1)
    if not r:
        return None
    return float(r[0]["lat"]), float(r[0]["lon"]), r[0]["display_name"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("address")
    ap.add_argument("--size", type=float, help="m²")
    ap.add_argument("--rooms", type=float)
    ap.add_argument("--warm", type=float, help="warm rent in EUR")
    ap.add_argument("--kalt", type=float, help="cold rent in EUR")
    ap.add_argument("--text", default="", help="the listing text, for feature matching")
    ap.add_argument("--profile", help="path to a profile other than profile.json")
    a = ap.parse_args()

    prof = P.load(a.profile)

    hit = geocode(a.address)
    if not hit:
        sys.exit(f"Nominatim could not place {a.address!r}. Try a fuller address.")
    lat, lng, display = hit
    print(f"\033[2m{display[:100]}\033[0m\n")

    # Progress, because the first run on an address nobody has looked at before
    # goes out to a router and to Overpass and can take a couple of minutes.
    # Without this it looks like it has hung, and the honest fix is to say what
    # it is doing rather than to make a stranger guess. Everything is cached
    # afterwards, so a second look at the same street is instant.
    def step(msg):
        print(f"  \033[2m… {msg}\033[0m", end="\r", flush=True)

    step("routing to the places you named")
    tier, tlabel = transit.tier(lat, lng, prof)
    mins  = transit.minutes_to_anchors(lat, lng, prof)
    step("counting what is nearby (first time here can take a minute)")
    hits  = places.measure(lat, lng, prof)
    step("reading the neighbourhood statistics")
    k     = kiez.lookup(lat, lng)
    transit.save()
    print(" " * 72, end="\r")

    warm, warm_real = P.warm_of(a.kalt, a.warm, prof)
    listing = dict(title=a.address, description=a.text, address=a.address,
                   size=a.size, rooms=a.rooms, kalt=a.kalt, warm=warm,
                   dist_km=round(transit.metres(lat, lng, 52.52, 13.405) / 1000, 1))

    scored = a.size and (a.warm or a.kalt)
    sc, flags = None, []
    if scored:
        sc, flags, parts = scoring.score(listing, prof, tier=tier,
                                         anchor_minutes=mins, nearby_hits=hits)

    gates = L.hard_hits((a.address + " " + a.text).lower(), a.address,
                        gate_pets=bool((prof.get("person") or {}).get("pets")))
    fails = [L.LABELS.get(g, g) for g in gates]

    print(card.render(dict(
        score=sc, addr=a.address, lat=lat, lng=lng, kiez=(k or {}).get("name"),
        warm=warm, warm_real=warm_real, kalt=a.kalt, size=a.size, rooms=a.rooms,
        transit=tlabel, anchors={x["label"]: mins.get(x["id"]) for x in prof["anchors"]},
        dist_km=listing["dist_km"], flags=flags, nearby=hits,
        check=card.checks(listing, prof), fails=fails,
    ), prof, markup=False))

    if not scored:
        print("\n\033[2mNo score: pass --size and --warm or --kalt to get one. "
              "Everything above is about the address, not the flat.\033[0m")
    else:
        print(f"\n\033[2mscore parts: {json.dumps(parts)}\033[0m")


if __name__ == "__main__":
    main()
