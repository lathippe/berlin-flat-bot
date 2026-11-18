#!/usr/bin/env python3
"""Build a search profile by asking.

Run this once, before anything else:

    python3 intake/interview.py

It asks what you are looking for and writes `profile.json` in the repo root.
Nothing else in this project has any opinion about flats: every gate, every
bonus and every line of the Telegram card comes out of that file. If the bot
sends you something wrong, the fix is almost always here, not in the code.

Design notes, because they shape the questions:

  * The last section is deliberately open. The fixed questions cover what most
    people need, and they will miss whatever matters to you specifically. That
    section exists so you can name it, and so does the `nearby` mechanism it
    writes into.

  * Questions about places ask for an address, not coordinates, and geocode it
    for you. Asking a person for a latitude is how a profile ends up with the
    office two streets away from the office.

  * Everything is optional. Press enter to skip and the key is left out, which
    means "do not gate on this". An empty profile is a working profile: it will
    just send you a lot of flats.

Re-running reads the existing profile and offers each stored answer as the
default, so it doubles as the editor.
"""
import json, os, pathlib, re, sys, time, urllib.parse, urllib.request

ROOT    = pathlib.Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile.json"
UA      = "berlin-flat-bot/1.0 (profile intake)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


# ─────────────────────────────── asking ────────────────────────────────────

def ask(q, default=None, hint=None):
    """One free-text question. Enter keeps the default, '-' clears it."""
    d = "" if default in (None, "") else f" [{default}]"
    if hint:
        print(f"\n  \033[2m{hint}\033[0m")
    try:
        a = input(f"{q}{d}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nstopped, nothing written")
        sys.exit(1)
    if a == "-":
        return None
    return a or default


def ask_num(q, default=None, hint=None, cast=float):
    while True:
        a = ask(q, default, hint)
        if a in (None, ""):
            return None
        try:
            return cast(str(a).replace(",", ".").replace("€", "").strip())
        except ValueError:
            print("  needs to be a number, or enter to skip")


def ask_yes(q, default=None):
    d = {True: "y", False: "n"}.get(default, "")
    while True:
        a = ask(f"{q} (y/n)", d)
        if a in (None, ""):
            return default
        if a.lower().startswith("y"):
            return True
        if a.lower().startswith("n"):
            return False


def ask_list(q, default=None, hint=None):
    """Comma-separated list."""
    cur = ", ".join(default or [])
    a = ask(q, cur, hint)
    if not a:
        return list(default or [])
    return [x.strip() for x in a.split(",") if x.strip()]


def section(title, blurb=""):
    print(f"\n\n\033[1m── {title} {'─' * max(0, 58 - len(title))}\033[0m")
    if blurb:
        print(f"\033[2m{blurb}\033[0m")


# ───────────────────────────── geocoding ───────────────────────────────────

def geocode(address):
    """Address to (lat, lng, display name). None if Nominatim has no idea."""
    q = address if "berlin" in address.lower() else address + ", Berlin"
    url = NOMINATIM + "?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "de"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        r = json.load(urllib.request.urlopen(req, timeout=20))
        time.sleep(1.1)                      # Nominatim asks for max 1 req/sec
    except Exception as exc:
        print(f"  \033[33mgeocoder unreachable ({type(exc).__name__}), skipping\033[0m")
        return None
    if not r:
        return None
    return float(r[0]["lat"]), float(r[0]["lon"]), r[0]["display_name"]


def ask_place(q, hint=None, existing=None):
    """Ask for an address and resolve it. Returns (lat, lng) or None."""
    if existing:
        keep = ask_yes(f"{q} is {existing.get('label')} at "
                       f"{existing['lat']:.4f},{existing['lng']:.4f}. Keep it?", True)
        if keep:
            return existing["lat"], existing["lng"]
    while True:
        a = ask(q, hint=hint)
        if not a:
            return None
        hit = geocode(a)
        if not hit:
            print("  \033[33mnot found. Try a fuller address, or enter to skip.\033[0m")
            continue
        lat, lng, name = hit
        print(f"  \033[2m→ {name[:88]}\033[0m")
        if ask_yes("  Is that the right place?", True):
            return lat, lng


# ───────────────────────────── the nearby catalogue ────────────────────────
#
# Presets for things people commonly want nearby. Each one names the dataset
# that answers it, because the answer is only as good as its source. Anything
# not in here can still be added by hand: see docs/nearby.md.

PRESETS = {
    "nursery": dict(
        label="Nursery / Kita", source="berlin-kita", query=None,
        radius_m=1000, want="many", weight=8,
        pitch="Nurseries within walking distance",
        note="Official Berlin Kita register. Addresses are reliable; free places are not in the data."),
    "primary_school": dict(
        label="Primary school", source="berlin-school", query={"type": "Grundschule"},
        radius_m=1500, want="many", weight=8,
        pitch="Primary schools nearby",
        note="Official Berlin school register. Catchment areas are not modelled, only distance."),
    "secondary_school": dict(
        label="Secondary school", source="berlin-school", query={"type": "Sekundarschule|Gymnasium"},
        radius_m=2500, want="many", weight=5,
        pitch="Secondary schools nearby", note="Official Berlin school register."),
    "playground": dict(
        label="Playground", source="overpass", query='nwr["leisure"="playground"]',
        radius_m=800, want="any", weight=4, pitch="A playground within a short walk",
        note="OpenStreetMap. Good coverage in Berlin."),
    "park": dict(
        label="Park or green space", source="overpass",
        query='nwr["leisure"~"^(park|garden)$"]', radius_m=800, want="any", weight=4,
        pitch="A park within a short walk", note="OpenStreetMap."),
    "supermarket": dict(
        label="Supermarket", source="overpass", query='nwr["shop"~"^(supermarket|convenience)$"]',
        radius_m=700, want="any", weight=3, pitch="A supermarket nearby", note="OpenStreetMap."),
    "gym": dict(
        label="Gym", source="overpass", query='nwr["leisure"="fitness_centre"]',
        radius_m=1500, want="any", weight=3, pitch="A gym nearby", note="OpenStreetMap."),
    "doctor": dict(
        label="GP / doctor", source="overpass", query='nwr["amenity"~"^(doctors|clinic)$"]',
        radius_m=1200, want="any", weight=3, pitch="A doctor nearby", note="OpenStreetMap."),
    "indian_community": dict(
        show_label=False, label="Indian community", source="overpass",
        query='nwr["cuisine"~"indian",i];nwr["religion"~"^(hindu|sikh)$",i];'
              'nwr["shop"]["name"~"\\\\b(india|indian|punjabi?|masala|tandoori?|bollywood|ayurveda)\\\\b",i]',
        radius_m=2500, want="many", weight=6,
        pitch="Indian shops, restaurants and temples nearby",
        note="PROXY, not a measurement. OpenStreetMap knows where Indian restaurants, "
             "grocers and Hindu or Sikh places of worship are. It does not know where "
             "Indian families live. Read docs/nearby.md before trusting the number."),
    "turkish_community": dict(
        show_label=False, label="Turkish community", source="overpass",
        query='nwr["cuisine"~"turkish",i];nwr["religion"="muslim"];'
              'nwr["shop"]["name"~"\\\\b(turk|anadolu|istanbul|bosphorus)\\\\b",i]',
        radius_m=2000, want="many", weight=5,
        pitch="Turkish shops, restaurants and mosques nearby",
        note="PROXY. Same caveat as above."),
    "place_of_worship": dict(
        show_label=False, label="Place of worship", source="overpass", query='nwr["amenity"="place_of_worship"]',
        radius_m=2000, want="any", weight=4, pitch="A place of worship of your faith nearby",
        note="OpenStreetMap. Set `query` by hand to pick the religion, see docs/nearby.md."),
}


def ask_nearby(existing):
    section("What has to be near the flat",
            "Each answer becomes a line in every listing the bot sends you, and\n"
            "optionally a filter. Skip anything you do not care about.")
    have = {n["id"]: n for n in (existing or [])}
    out = []
    for pid, p in PRESETS.items():
        cur = have.get(pid)
        want = ask_yes(f"{p['pitch']}?", cur is not None)
        if not want:
            continue
        radius = ask_num("  Within how many metres", (cur or p)["radius_m"], cast=int)
        entry = dict(id=pid, label=p["label"], source=p["source"], query=p["query"],
                     radius_m=radius or p["radius_m"], want=p["want"], weight=p["weight"])
        if p.get("show_label") is False:
            entry["show_label"] = False
        if ask_yes("  Reject flats that have none in that radius?", bool((cur or {}).get("min_count"))):
            entry["min_count"] = ask_num("  Minimum number", (cur or {}).get("min_count", 1), cast=int) or 1
        if p.get("note"):
            print(f"  \033[2m{p['note']}\033[0m")
        out.append(entry)

    # The open question. Everything above is a guess about what people want;
    # this is where the things nobody guessed get recorded.
    section("Anything else",
            "Name anything that has to be near your flat that was not asked about.\n"
            "It gets written into the profile with source \"manual\" and a note, so it\n"
            "is visible and waiting rather than silently lost. Enter to finish.")
    while True:
        what = ask("Something else that must be nearby")
        if not what:
            break
        radius = ask_num("  Within how many metres", 1500, cast=int)
        out.append(dict(id=re.sub(r"\W+", "_", what.lower())[:30], label=what,
                        source="manual", query=None, radius_m=radius or 1500,
                        want="any", weight=4,
                        todo="No data source wired up yet. See docs/nearby.md to add one."))
        print("  \033[2mrecorded. It will show in the profile but will not be measured "
              "until a source is wired up.\033[0m")
    return out


# ───────────────────────────── priorities ──────────────────────────────────
#
# Without this section the bot runs on somebody else's priorities. The defaults
# it would otherwise use came out of one person's search, where being far from
# the centre was close to disqualifying and public transport at the door was
# the single biggest weight. For somebody with a family and a car that is
# simply wrong, and wrong in a way that is invisible: the bot keeps working,
# it just quietly ranks the wrong flats first.
#
# Ratings rather than numbers, because nobody can say "transport is worth 25".
# Everything is relative, so saying "a lot" to several is fine and normal.

DIMENSIONS = [
    ("transit",       "Public transport at the door"),
    ("area",          "Being in a neighbourhood you like"),
    ("anchors",       "Short travel time to the places you named"),
    ("centre",        "Being close to the city centre"),
    ("rent",          "The rent itself, in euros"),
    ("price_per_sqm", "Getting good value per square metre"),
    ("size",          "Size of the flat"),
    ("rooms",         "Number of rooms"),
    ("nearby",        "Having the things you listed nearby"),
]

SCALE = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def ask_priorities(existing):
    section("What decides it",
            "Rate how much each one matters to you. These are weighed against each\n"
            "other, so answering \"a lot\" to several is fine.\n\n"
            "  0  does not matter        3  a lot\n"
            "  1  a little               5  this is what decides it\n"
            "  2  quite a bit")
    old_w = (existing or {}).get("_ratings") or {}
    raw = {}
    for key, label in DIMENSIONS:
        while True:
            a = ask(f"  {label}", old_w.get(key, 3))
            if a is None:
                raw[key] = 0
                break
            try:
                v = int(str(a).strip())
            except ValueError:
                print("  a number from 0 to 5")
                continue
            if 0 <= v <= 5:
                raw[key] = v
                break
            print("  a number from 0 to 5")

    total = sum(raw.values())
    if not total:
        print("  \033[33mEverything rated zero, so nothing can be ranked. "
              "Using balanced weights instead.\033[0m")
        raw = {k: 3 for k, _ in DIMENSIONS}
        total = sum(raw.values())

    # Share out 100 points in proportion. anchors and nearby are budgets that
    # get split across their own entries further down.
    weights = {k: round(v / total * 100, 1) for k, v in raw.items()}
    print("\n  Out of 100, that comes to:")
    for k, _label in sorted(DIMENSIONS, key=lambda d: -weights[d[0]]):
        if weights[k]:
            bar = "█" * max(1, int(weights[k] / 2))
            print(f"    {dict(DIMENSIONS)[k]:38} {weights[k]:5.1f}  {bar}")
    zero = [dict(DIMENSIONS)[k] for k, _ in DIMENSIONS if not weights[k]]
    if zero:
        print(f"    \033[2mignored entirely: {', '.join(zero)}\033[0m")
    return weights, raw


def apply_priorities(weights, anchors, nearby):
    """Split the anchors and nearby budgets across their own entries."""
    a_budget, n_budget = weights.pop("anchors", 0), weights.pop("nearby", 0)
    if anchors:
        # The first anchor is usually the office and carries most of the weight.
        share = [2.0] + [1.0] * (len(anchors) - 1)
        tot = sum(share)
        for a, sh in zip(anchors, share):
            a["weight"] = round(a_budget * sh / tot, 1)
    if nearby:
        base = sum(float(n.get("weight") or 1) for n in nearby) or 1
        for n in nearby:
            n["weight"] = round(n_budget * float(n.get("weight") or 1) / base, 1)
    return weights


def ask_delivery(existing):
    section("Where should it reach you",
            "Three options, and they are not equally good for this.")
    d = dict(existing or {})
    print("""
  telegram   Least work and the best fit. A bot token takes two minutes, costs
             nothing, and the message renders properly with a map.
  email      Most portable. Works on any phone with nothing installed, and the
             alerts land next to the replies from landlords. Slower to notice,
             which costs you in a market where a good flat goes in a day.
  whatsapp   The one that fights back. Meta only lets a business message you
             freely inside 24 hours of you writing to it; outside that window
             only pre-approved templates go through, and a template cannot
             carry a flat card. Workable through Twilio's sandbox, which needs
             re-joining every 72 hours and costs per message.
""")
    while True:
        ch = (ask("Channel", d.get("channel", "telegram")) or "telegram").strip().lower()
        if ch in ("telegram", "email", "whatsapp"):
            break
        print("  one of: telegram, email, whatsapp")
    out = {"channel": ch}

    if ch == "telegram":
        out["telegram_chat_id"] = ask(
            "  Telegram chat id", d.get("telegram_chat_id"),
            hint="Message @userinfobot on Telegram and it replies with your id.\n"
                 "You also have to message your own bot once before it may message you.")
    elif ch == "email":
        out["email"] = ask("  Send to which address", d.get("email"))
        if ask_yes("  Use your own SMTP server rather than Gmail?", bool(d.get("smtp_host"))):
            out["smtp_host"] = ask("  SMTP host", d.get("smtp_host"))
            out["smtp_port"] = ask_num("  Port", d.get("smtp_port", 587), cast=int)
            out["smtp_user"] = ask("  Username", d.get("smtp_user"))
            print("  \033[2mThe password goes in ~/.config/berlin-flat-bot/smtp_password, "
                  "never in the profile.\033[0m")
        else:
            print("  \033[2mIt will send through the same Gmail credentials the mail "
                  "watcher uses, so there is only one secret to manage.\033[0m")
    else:
        out["whatsapp"] = ask("  Your WhatsApp number, with country code",
                              d.get("whatsapp"), hint="e.g. +4915112345678")
        print("  \033[2mTwilio credentials go in ~/.config/berlin-flat-bot/twilio_sid "
              "and twilio_token. See docs/delivery.md.\033[0m")
    return {k: v for k, v in out.items() if v not in (None, "")}


# ──────────────────────────────── main ─────────────────────────────────────

def main():
    old = {}
    if PROFILE.exists():
        old = json.loads(PROFILE.read_text())
        print(f"\033[2mEditing the existing {PROFILE.name}. Enter keeps each stored "
              f"answer, '-' clears it.\033[0m")
    else:
        print(__doc__.split("\n\n")[0])

    p   = old.get("person", {})
    bud = old.get("budget", {})
    hm  = old.get("home", {})
    tr  = old.get("transit", {})
    ar  = old.get("areas", {})

    section("You", "Only the chat id matters to the bot. The rest is quoted in\n"
                   "application drafts later on.")
    person = {
        "name": ask("Your name", p.get("name")),
        "household": ask("Who is moving in", p.get("household"),
                         hint="Free text, e.g. \"me, my wife and two children\"."),
    }
    kids = ask("Children's ages, comma separated", ", ".join(str(a) for a in p.get("children", [])))
    if kids:
        person["children"] = [int(x) for x in re.findall(r"\d+", kids)]
    # Only asked because it changes behaviour. With no pet the "no pets" gate is
    # switched off entirely and the card stops telling you to check a pet policy
    # you do not need, instead of carrying a question that is not yours.
    pets = ask_list("Pets, comma separated, or enter for none", p.get("pets"),
                    hint="A lot of Berlin listings ban them outright. With a pet listed,\n"
                         "the bot rejects those for you. With none, it ignores the subject.")
    if pets:
        person["pets"] = pets

    section("Money", "Warm rent means rent including Nebenkosten. Listings that quote\n"
                     "only Kaltmiete are estimated by multiplying, see warm_factor.")
    budget = {
        "max_warm":    ask_num("Hard ceiling, warm EUR", bud.get("max_warm"),
                               hint="Above this nothing is ever shown."),
        "target_warm": ask_num("Comfortable level, warm EUR", bud.get("target_warm"),
                               hint="Still shown above this, but loses points. Enter to skip."),
        "warm_factor": ask_num("Kalt to warm multiplier", bud.get("warm_factor", 1.3)),
        "extras_monthly": ask_num("Electricity and internet per month, EUR",
                                  bud.get("extras_monthly"),
                                  hint="Paid on top of warm. Shown in the card so you see the real figure."),
    }
    if ask_yes("Allow an exception above the ceiling for an outstanding flat?",
               bool(bud.get("stretch_warm"))):
        budget["stretch_warm"]  = ask_num("  Absolute maximum, warm EUR", bud.get("stretch_warm"))
        budget["stretch_score"] = ask_num("  Score out of 100 it must reach to qualify",
                                          bud.get("stretch_score", 85))
    budget = {k: v for k, v in budget.items() if v is not None}

    section("The flat")
    home = {
        "min_size_sqm": ask_num("Minimum size, m²", hm.get("min_size_sqm")),
        "min_rooms":    ask_num("Minimum rooms", hm.get("min_rooms")),
        "max_floor_no_lift": ask_num("Highest floor you would accept without a lift",
                                     hm.get("max_floor_no_lift"), cast=int),
    }
    home["wants"] = ask_list("Nice to have, comma separated", hm.get("wants"),
                             hint="e.g. balcony, bathtub, elevator, fitted kitchen, garden, quiet courtyard")
    home["deal_breakers"] = ask_list("Absolute no, comma separated", hm.get("deal_breakers"),
                                     hint="Phrases that reject a listing on sight. e.g. Tauschwohnung,\n"
                                          "WG, Zwischenmiete, befristet, no pets, ground floor")
    home = {k: v for k, v in home.items() if v not in (None, [], "")}

    section("Places you must reach",
            "The bot measures a door-to-door public transport trip to each of these\n"
            "and prints it on every listing.")
    anchors, old_anchors = [], {a["id"]: a for a in old.get("anchors", [])}
    office = ask_place("Office address", existing=old_anchors.get("office"),
                       hint="Enter to skip if you have no fixed workplace.")
    if office:
        anchors.append(dict(id="office", label="office", lat=office[0], lng=office[1],
                            max_minutes=ask_num("  Longest acceptable trip, minutes",
                                                old_anchors.get("office", {}).get("max_minutes", 45),
                                                cast=int),
                            weight=15))
    while ask_yes("Another place you need to reach regularly?",
                  len([a for a in old.get('anchors', []) if a['id'] != 'office']) > 0 and not anchors):
        label = ask("  What is it", hint="e.g. school, gym, parents, partner's flat")
        if not label:
            break
        pl = ask_place(f"  {label} address")
        if not pl:
            break
        anchors.append(dict(id=re.sub(r"\W+", "_", label.lower())[:20], label=label,
                            lat=pl[0], lng=pl[1],
                            max_minutes=ask_num("  Longest acceptable trip, minutes", cast=int),
                            weight=5))
    for a in anchors:
        if a.get("max_minutes") is None:
            a.pop("max_minutes", None)

    section("Getting around")
    modes = []
    if ask_yes("Does U-Bahn / S-Bahn count as connected?", "rail" in (tr.get("modes") or ["rail"])):
        modes.append("rail")
    if ask_yes("Does tram count?", "tram" in (tr.get("modes") or ["tram"])):
        modes.append("tram")
    if ask_yes("Does bus count?", "bus" in (tr.get("modes") or [])):
        modes.append("bus")
    transit = {"modes": modes,
               "max_walk_min": ask_num("Longest walk to a stop, minutes",
                                       tr.get("max_walk_min", 12), cast=int)}
    if not modes:
        print("  \033[33mNothing counts as connected, so the transit gate is off.\033[0m")

    section("Areas")
    areas = {
        "never": ask_list("Areas you will not live in", ar.get("never"),
                          hint="District or neighbourhood names. Matched against the address.\n"
                               "fredy/providers/never-areas.js has to be kept in step, see docs/fredy.md."),
        "favourite": ask_list("Areas you would love", ar.get("favourite")),
        "low_priority": ask_list("Areas you would accept but reluctantly", ar.get("low_priority")),
    }
    areas["max_km_center"] = ask_num("Maximum straight-line distance from Mitte, km",
                                     ar.get("max_km_center"),
                                     hint="Only used as a fallback when no route can be computed.")
    areas = {k: v for k, v in areas.items() if v not in (None, [], "")}

    nearby = ask_nearby(old.get("nearby"))
    delivery = ask_delivery(old.get("delivery"))
    weights, ratings = ask_priorities(old.get("weights"))
    weights = apply_priorities(weights, anchors, nearby)

    out = {"person": {k: v for k, v in person.items() if v},
           "budget": budget, "home": home, "anchors": anchors,
           "transit": transit, "areas": areas, "nearby": nearby,
           "delivery": delivery,
           "weights": dict(weights, _ratings=ratings),
           "report": old.get("report", {"kiez_stats": True, "commute": True,
                                        "nearby": True, "map_preview": True,
                                        "language": "en"})}

    PROFILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\n\033[1mWritten to {PROFILE}\033[0m")
    todo = [n for n in nearby if n.get("todo")]
    if todo:
        print("\nStill needs a data source before it can be measured:")
        for n in todo:
            print(f"  · {n['label']}  → docs/nearby.md")
    print("\nNext: docs/setup.md step 2.")


if __name__ == "__main__":
    main()
