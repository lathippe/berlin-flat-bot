#!/usr/bin/env python3
"""Regression tests for src/listings.py.

    python3 tests/test_listings.py

Every case here is a listing that actually went wrong once: either it got
through and wasted an evening, or it was a decent flat that got thrown away.
The FALSE POSITIVE cases matter as much as the others. Most of the complexity
in listings.py exists to stop a gate firing on ordinary German prose, and a
"simplification" that breaks one of those looks like an improvement until the
bot goes quiet.

These expectations were verified against the original single-user implementation
on the day of the port: 21 of 21 identical, including every negation case.
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
import listings as L

# (name, title, pets_are_a_gate, expected gate ids)
CASES = [
    # ── gates that must fire ────────────────────────────────────────────────
    ("WBS required",      "Schöne 2-Zimmer-Wohnung, WBS erforderlich", False, ["wbs"]),
    ("income capped",     "Das Haushaltsnettoeinkommen darf 40.000 Euro nicht überschreiten",
                          False, ["income_cap"]),
    ("senior housing",    "Wohnen ab 55 in ruhiger Lage", False, ["age_restricted"]),
    ("sublet",            "Zwischenmiete für 3 Monate, möbliert", False,
                          ["fixed_term", "sublet_or_hotel"]),
    ("room in a flatshare", "Zimmer in netter WG zu vermieten", False, ["flatshare_or_room"]),
    ("weekly rate",       "2 Zimmer direkt am Görlitzer Park, Wochenpreis!", False,
                          ["price_not_monthly"]),
    ("swap only",         "NUR TAUSCH: 2 Zimmer gegen 3 Zimmer", False, ["swap_not_rental"]),
    ("shop unit",         "Ladenlokal im Erdgeschoss zu vermieten", False, ["not_residential"]),
    ("shell flat",        "Entkernt, Bastlerobjekt mit Ofenheizung", False, ["uninhabitable"]),
    ("fixed term by date","Verfügbar vom 01.12.2026 bis 31.03.2027", False, ["fixed_term"]),
    ("pets, gated",       "Keine Haustiere erlaubt", True, ["pets_forbidden"]),

    # ── negations that must switch a gate back off ──────────────────────────
    ("no WBS needed",     "Schöne Wohnung, kein WBS erforderlich", False, []),
    ("explicitly no swap","Kein Tausch, normale Vermietung, 2 Zimmer", False, []),

    # ── FALSE POSITIVES: ordinary prose a gate must not fire on ─────────────
    ("income only listed as a document to bring",
     "Bitte Angaben zum monatlichen Haushaltsnettoeinkommen mitbringen", False, []),
    ("'ab' is a date, not an age",
     "Wohnen ab 01.10.2026 möglich", False, []),
    ("a desk chair is not an office",
     "Bürostuhl und Schreibtisch vorhanden, Zimmer als Büro nutzbar", False, []),
    ("businesses described in the area, not the unit",
     "Ruhige Lage, keine Gewerbeansiedlungen in der Nähe", False, []),
    ("twice a week is a viewing slot, not a rental term",
     "Besichtigung zweimal pro Woche möglich", False, []),
    ("cosmetic work is a flag, never a gate",
     "Renovierungsbedürftig, viel Gestaltungspotenzial", False, []),
    ("pets not gated when the profile has no pet",
     "Keine Haustiere erlaubt", False, []),
    ("an ordinary good listing",
     "Helle 2-Zimmer-Wohnung mit Balkon und Einbauküche, unbefristet", False, []),
]

REQUESTS = [
    ("looking, not offering", "Bin auf dringende Wohnungssuche. 2 Zimmer, Kaltmiete bis 900 €", True),
    ("offering, despite the word suche",
     "Ich suche für meine Wohnung einen Nachmieter ab Dezember", False),
    ("plain offer", "Helle 2-Zimmer-Wohnung zu vermieten, provisionsfrei", False),
]

FEATURES = [
    ("Loggia counts as a balcony", "Wohnung mit großer Loggia", ["balcony"], "balcony"),
    ("Dachterrasse counts too",    "Dachterrasse nach Süden",   ["balcony"], "balcony"),
    # The card is English even though the listing is German, and American
    # English at that: the output says balcony and elevator, never Balkon or lift.
    ("Aufzug shows as elevator",   "Altbau mit Aufzug",         ["elevator"], "elevator"),
    ("'lift' is accepted as a spelling of elevator",
     "Altbau mit Fahrstuhl", ["lift"], "elevator"),
    ("Badewanne shows as bathtub", "Großes Bad mit Badewanne",  ["bathtub"], "bathtub"),
    ("unbefristet is not befristet", "Mietvertrag unbefristet",
     ["unlimited contract"], "unlimited contract"),
]


def main():
    bad = 0
    for name, text, gate_pets, want in CASES:
        got = sorted(L.hard_hits(text.lower(), text, gate_pets=gate_pets))
        if got != sorted(want):
            bad += 1
            print(f"FAIL  {name}\n        want {sorted(want)}\n        got  {got}")
    for name, text, want in REQUESTS:
        got = L.is_request(text.lower())
        if got != want:
            bad += 1
            print(f"FAIL  {name}: is_request want {want}, got {got}")
    for name, text, wanted, flag in FEATURES:
        _pts, flags = L.features(text.lower(), wanted=wanted)
        if flag not in flags:
            bad += 1
            print(f"FAIL  {name}: expected flag {flag!r}, got {flags}")

    total = len(CASES) + len(REQUESTS) + len(FEATURES)
    print(f"{total - bad}/{total} passed")
    # befristet must never be read as unbefristet: the lookbehind is load-bearing
    pts, _ = L.features("mietvertrag befristet auf 2 jahre", wanted=["unlimited contract"])
    if pts:
        print("FAIL  'befristet' scored as 'unbefristet'")
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
