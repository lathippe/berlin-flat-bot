#!/usr/bin/env python3
"""Regenerate fredy/providers/never-areas.js from profile.json.

Fredy needs its own copy of the "areas I will not live in" list, because it
filters while scraping and never sees this repo. Keeping two lists in step by
hand is a standing invitation to a silent bug: out of step, Fredy keeps
fetching flats in areas you ruled out and the bot quietly drops them, which
looks exactly like Fredy being broken.

So the profile is the only place you edit, and this writes the copy.

    python3 fredy/sync-never-areas.py

Run it after every change to areas.never, then rebuild Fredy's image.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROF = ROOT / "profile.json"
OUT  = ROOT / "fredy" / "providers" / "never-areas.js"

TEMPLATE = '''/*
 * Areas to skip, as a regular expression.
 *
 * GENERATED FILE. Do not edit by hand: `python3 fredy/sync-never-areas.py`
 * rewrites it from areas.never in profile.json, which is the source of truth.
 *
 * Why a copy exists at all: Fredy matches only a listing's title and
 * description while scraping, and the district usually lives in the address.
 * Filtering here saves fetching pages the bot would discard anyway.
 *
 * Generated from %d entries.
 */
const NEVER = [
%s
];

const NEVER_RX = NEVER.length ? new RegExp(NEVER.join('|'), 'i') : null;

/**
 * False when any part of the address falls in a skipped area.
 * @param {...(string|null|undefined)} parts Address, title, district, whatever exists.
 */
export function inServiceArea(...parts) {
  if (!NEVER_RX) return true;
  return !parts.filter(Boolean).some((p) => NEVER_RX.test(String(p)));
}
'''


def main():
    if not PROF.exists():
        sys.exit("profile.json not found. Run intake/interview.py first.")
    never = (json.loads(PROF.read_text()).get("areas") or {}).get("never") or []
    if not never:
        print("areas.never is empty: Fredy will not filter on area at all.")
    rows = []
    for n in never:
        # Entries are written by humans as place names. Escape anything that
        # would otherwise be a regex metacharacter, but leave an entry that is
        # clearly already a pattern (contains \b, |, [] ) alone.
        looks_like_rx = bool(re.search(r"\\b|\||\[|\(", n))
        rows.append("  '%s'," % (n if looks_like_rx else re.escape(n).replace("'", "\\'")))
    OUT.write_text(TEMPLATE % (len(never), "\n".join(rows) if rows else ""))
    print(f"wrote {OUT.relative_to(ROOT)} with {len(never)} entries")
    if never:
        print("  " + ", ".join(never[:8]) + (" ..." if len(never) > 8 else ""))
    print("Rebuild Fredy's image for it to take effect.")


if __name__ == "__main__":
    main()
