#!/usr/bin/env python3
"""Load profile.json and fill in what it does not say.

Everything the bot believes about what a good flat is comes through here. The
defaults below are what you get when the interview skipped a question, and they
are deliberately loose: an unanswered question should widen the search, not
silently narrow it.

The one exception is `weights`. Those are not preferences, they are how the
100 points are divided, and they have real defaults because somebody has to
decide and most people have no opinion until they have seen a week of results.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Fallback only, for a profile written before the interview asked about
# priorities. Anything produced by `intake/interview.py` carries its own
# weights and never reaches these.
#
# They came out of one person's search, and they are that person's priorities,
# not general truth: being far from the centre was nearly disqualifying and
# transport at the door was the single largest weight. For somebody with a
# family, a car, or a job they drive to, that is simply the wrong shape, and
# wrong invisibly: the bot keeps working and just ranks the wrong flats first.
#
#   transit 25   The biggest single weight, because it is the thing you cannot
#                change about a flat and the thing you feel every single day.
#   area    20   Where you actually want to be.
#   ppm     15   Price per m2 against the market band: catches the overpriced
#                and flags the suspiciously cheap.
#   rent    10   The absolute figure, separately. Without this the scorer
#                happily recommends more square metres at a higher rent, which
#                is the opposite of the point.
#   size    10   A band with a peak, not "bigger is better". Extra rooms are
#                extra cleaning and extra heating.
#   centre   8   Was 15. Dropped after it became clear that with an office
#                visited once a week, distance was quietly worth 40 of 100.
#   rooms    5
#
# Anchors and nearby entries add their own weights on top, declared per entry
# in the profile, and the total is normalised at the end.
DEFAULT_WEIGHTS = {
    "transit": 25, "area": 20, "price_per_sqm": 15,
    "rent": 10, "size": 10, "centre": 8, "rooms": 5,
}

DEFAULTS = {
    "budget": {"warm_factor": 1.3},
    "home":   {"sweet_size": [45, 65], "wants": [], "deal_breakers": []},
    "transit": {"modes": ["rail", "tram"], "max_walk_min": 12},
    "areas":  {"never": [], "favourite": [], "low_priority": [], "ok": []},
    "nearby": [],
    "report": {"kiez_stats": True, "commute": True, "nearby": True,
               "map_preview": True, "language": "en"},
    # Berlin asking-rent band, EUR per m2 cold. Below the first number is
    # cheap enough to be worth a second look at why; above the second is
    # expensive for what it is.
    "market_ppm": [12.0, 17.0],
    "min_score": 52,
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        elif v not in (None, ""):
            out[k] = v
    return out


def load(path=None):
    p = pathlib.Path(path) if path else ROOT / "profile.json"
    if not p.exists():
        raise SystemExit(
            f"No profile at {p}.\nRun `python3 intake/interview.py` first: "
            f"nothing in this bot has an opinion without it.")
    prof = _merge(DEFAULTS, json.loads(p.read_text()))
    # The interview's answers win outright. Merging them into the defaults
    # would quietly reinstate a dimension the person rated zero, which is the
    # whole thing this section exists to prevent: a weight nobody chose,
    # reordering results invisibly. Defaults apply only when the profile
    # predates the priorities question and has no weights at all.
    w = dict(prof.get("weights") or {})
    prof["_ratings"] = w.pop("_ratings", None)
    prof["weights"] = w or dict(DEFAULT_WEIGHTS)
    _derive_sweet_size(prof)
    _check(prof)
    return prof


def _derive_sweet_size(prof):
    """Keep the ideal-size band consistent with the minimum that was asked for.

    The band defaults to 45-65 m2, which was one person's answer and is wrong
    for anybody with a family. Without this, somebody who says "at least 75 m2"
    gets an 82 m2 flat scored as "more space than needed", which is the exact
    opposite of what they said. So unless the band is set explicitly, it starts
    at the stated minimum and runs a third above it.
    """
    home = prof.setdefault("home", {})
    if home.get("sweet_size") and home["sweet_size"] != DEFAULTS["home"]["sweet_size"]:
        return                                   # set by hand, leave it alone
    lo = home.get("min_size_sqm")
    if lo and lo > DEFAULTS["home"]["sweet_size"][0]:
        home["sweet_size"] = [float(lo), round(float(lo) * 1.35)]


def _check(p):
    """Shout about the mistakes that quietly produce an empty inbox."""
    warn = []
    b = p.get("budget") or {}
    if not b.get("max_warm"):
        warn.append("budget.max_warm is not set, so nothing is capped by rent.")
    if b.get("target_warm") and b.get("max_warm") and b["target_warm"] > b["max_warm"]:
        warn.append("budget.target_warm is above max_warm, which cannot be met.")
    if not (p.get("transit") or {}).get("modes"):
        warn.append("transit.modes is empty, so no address counts as connected.")
    if not p.get("anchors"):
        warn.append("No anchors, so no travel time is checked or shown.")
    for n in p.get("nearby") or []:
        if n.get("min_count") and n.get("source") == "manual":
            warn.append(f"nearby '{n.get('id')}' has no data source but sets min_count. "
                        f"It will never reject anything, which is the safe behaviour, "
                        f"but it is probably not what you meant.")
    for w in warn:
        print(f"  profile: {w}")
    return warn


def warm_of(kalt, warm, prof):
    """Warm rent, estimated from cold when the listing does not give it.

    Returns (figure, is_real). The flag reaches the card, because "1 480 EUR
    warm" and "about 1 480 EUR warm, estimated" are different claims and the
    second one has been wrong by two hundred euros before.
    """
    if warm:
        return float(warm), True
    if kalt:
        return float(kalt) * float((prof.get("budget") or {}).get("warm_factor", 1.3)), False
    return None, False


def over_budget(warm, prof, score=None):
    """True when the rent disqualifies the flat.

    Two ceilings. `max_warm` is the ordinary one. `stretch_warm`, when set,
    lets an exceptional flat through between the two, but only if it reached
    `stretch_score`. The score already drops for rent above `target_warm`, so
    clearing the stretch bar at the top of the range takes a genuinely good
    flat rather than an expensive one.
    """
    b = prof.get("budget") or {}
    cap = b.get("max_warm")
    if not warm or not cap:
        return False
    if warm <= cap:
        return False
    stretch = b.get("stretch_warm")
    if not stretch or warm > stretch:
        return True
    return score is None or score < (b.get("stretch_score") or 85)


if __name__ == "__main__":
    import sys
    p = load(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({"weights": p["weights"],
                      "max_warm": (p.get("budget") or {}).get("max_warm"),
                      "anchors": [a["label"] for a in p.get("anchors", [])],
                      "nearby": [n["id"] for n in p.get("nearby", [])],
                      "never": p["areas"]["never"]}, indent=2, ensure_ascii=False))
