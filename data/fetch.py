#!/usr/bin/env python3
"""Download the Berlin reference datasets this bot needs. Run once, then after
a school year or so to refresh.

    python3 data/fetch.py

Both come from Berlin's official spatial data infrastructure (gdi.berlin.de) as
WFS, which hands back coordinates directly. The alternative published format is
an XLSX of addresses, which would mean geocoding three thousand rows through
Nominatim at one request per second. This takes four seconds instead.

Written files:
    data/kita.json      ~2900 nurseries: name, places, address, lat, lng
    data/schools.json   ~930 schools: name, kind, state or private, lat, lng

Licence: Datenlizenz Deutschland Namensnennung 2.0. Attribution is in README.
"""
import json, pathlib, sys, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
UA   = "berlin-flat-bot/1.0"

SOURCES = {
    "kita.json": dict(
        base="https://gdi.berlin.de/services/wfs/kita", layer="kita:kita",
        fields=lambda p: {
            "name":   p.get("e_name"),
            "kind":   p.get("e_art"),
            "places": p.get("e_platz"),
            "addr":   " ".join(x for x in (p.get("e_strasse"), p.get("e_hnr")) if x).strip(),
            "plz":    p.get("e_plz"),
        }),
    "schools.json": dict(
        base="https://gdi.berlin.de/services/wfs/schulen", layer="schulen:schulen",
        fields=lambda p: {
            "name":   p.get("schulname"),
            "kind":   p.get("schulart"),
            "type":   p.get("schultyp"),
            "owner":  p.get("traeger"),
            "addr":   " ".join(x for x in (p.get("strasse"), p.get("hausnr")) if x).strip(),
            "plz":    p.get("plz"),
        }),
}


def fetch(base, layer):
    url = (f"{base}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames={layer}&outputFormat=application/json&srsName=EPSG:4326")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=180))


def main():
    for fname, src in SOURCES.items():
        print(f"{fname} ... ", end="", flush=True)
        try:
            gj = fetch(src["base"], src["layer"])
        except Exception as exc:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            print("  The service is occasionally down. Try again in a few minutes.")
            continue
        out = []
        for f in gj.get("features", []):
            g = (f.get("geometry") or {})
            if g.get("type") != "Point":
                continue
            lng, lat = g["coordinates"][:2]
            rec = src["fields"](f.get("properties") or {})
            rec["lat"], rec["lng"] = round(lat, 6), round(lng, 6)
            out.append(rec)
        (HERE / fname).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        kinds = {}
        for r in out:
            kinds[r.get("kind") or "?"] = kinds.get(r.get("kind") or "?", 0) + 1
        top = ", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:4])
        print(f"{len(out)} records  ({top})")


if __name__ == "__main__":
    main()
