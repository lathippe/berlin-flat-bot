#!/usr/bin/env python3
"""What a German rental listing is actually saying.

This module is the one part of the bot that is the same for everybody. It has
no opinions about budget or neighbourhoods: it only knows how Berlin landlords
write, and how to tell a flat you can rent from one you cannot.

Every pattern here was paid for by a listing that got through and wasted an
evening, or by a good flat that was thrown away. The comments say which. Do not
simplify one without knowing what it was for.

Two things to understand before editing:

* **Negations matter more than keywords.** "WBS erforderlich" and "kein WBS
  erforderlich" differ by one word and mean opposite things. Every gate that
  can be negated has a matching NO_* pattern, and `hard_hits` applies it.

* **Word boundaries are not optional.** `gewerbe` without one matches
  "Gewerbeansiedlungen" in a description of the neighbourhood, which is a
  selling point, not a commercial unit. The lookaheads in `not_residential`ate
  all there for a specific listing that was wrongly dropped.
"""
import re

# ── The hard gates ──────────────────────────────────────────────────────────
#
# (id, human label, pattern). A match means the listing is not a flat this
# person can rent, so the work stops there. Order is cheapest first.
#
#   wbs                 a social housing certificate most people do not have
#   income_cap          rent tied to an income ceiling. The bare word
#                       "Haushaltsnettoeinkommen" is not enough: it also
#                       appears in the list of documents to bring. A cap says
#                       "nicht ueberschreiten", "maximal", "bis zu" nearby.
#   age_restricted      senior housing. "Wohnen ab 55" is usually written
#                       without the word Jahren, and the [5-9]\d range keeps
#                       "Wohnen ab 01.10.2026" from reading as an age.
#   sublet_or_hotel     Zwischenmiete, holiday lets, boarding houses
#   flatshare_or_room   a room, not a flat
#   price_not_monthly   a weekly or nightly rate. 300 EUR for 50 m2 reads as a
#                       bargain at 6 EUR/m2 and is really ~1300 a month.
#   swap_not_rental     wohnungsswap.de cross-posts to immowelt. Only useful if
#                       you have a flat to trade. A bare "Tausch" anywhere now
#                       counts, after one got through titled "NUR TAUSCH:".
#   not_residential     offices, shops, storage. The lookaheads exclude a desk
#                       chair, a room usable as a study, and a neighbourhood
#                       described as having businesses in it.
#   pets_forbidden      only a gate when the profile lists a pet
#   uninhabitable       shell flats, coal stoves, a bathroom on the landing.
#                       Cosmetic work is NOT here: it is a flag and a lever on
#                       the price, not a reason to skip the viewing.

HARD = [
    ("wbs", "needs a WBS certificate",
     "wbs|wohnberechtigungsschein"),
    ("income_cap", "income is capped",
     "einkommensorientiert|einkommensgrenze|haushaltsnettoeinkommen(?:[^.]|\\.(?=\\d)){0,60}(?:nicht [üu]berschreiten|maximal|max\\.|h[öo]chstens|bis zu)|(?:maximal|max\\.|h[öo]chstens)(?:[^.]|\\.(?=\\d)){0,40}haushaltsnettoeinkommen"),
    ("age_restricted", "age restricted",
     "\\bab \\d{2} jahren|senioren(?:wohn|residenz|heim|anlage|gerecht|-?wg)|(?:nur|ausschlie[ßs]lich)\\s+(?:f[üu]r\\s+)?senioren|wohnen\\s+f[üu]r\\s+senioren|betreutes|(?:wohnen|zuhause|leben)\\s+ab\\s+[5-9]\\d\\b(?!\\s*(?:m²|qm|€|eur)|\\.\\d)"),
    ("sublet_or_hotel", "sublet or short stay",
     "zwischenmiete|untermiete|unter(?:zu)?vermiet|vermiete[^.]{0,60}\\bunter\\b|sublet|ferienwohn|monteur|boardinghouse|apartmenthaus|serviced|zeitwohnen|kurzzeit|short.?term|student(?:en)? ?(?:housing|wohnen|apartment)"),
    ("flatshare_or_room", "flatshare or single room",
     "\\bwg\\b|wohngemeinschaft|zimmer in |mitbewohner|studentinnen"),
    ("price_not_monthly", "price is not monthly",
     "wochenpreis|tagespreis|preis\\s*(?:pro|je)\\s*(?:woche|nacht|tag)|\\d+\\s*€?\\s*(?:pro|je|/)\\s*(?:woche|nacht|tag)\\b|\\d\\s*x\\s*woche|(?:pro|je)\\s*woche\\s*=?\\s*\\d+\\s*€|per week|price per (?:week|night)|weekly (?:price|rate|rent)|per night"),
    ("swap_not_rental", "a swap, not a rental",
     "wohnungsswap|wohnungstausch|tauschwohnung|tauschpartner|tauschangebot|tauschobjekt|\\btausch(?:e|en)?\\b|(?:wohnungs?|apartment|flat|home)[ -]?(?:swap|exchange)|\\bswap\\b|\\bexchange only\\b|\\bonly (?:for )?exchange\\b|apartment of (?:my|our|his|her|their|your) own|own (?:apartment|flat) to exchange"),
    ("not_residential", "not residential",
     "(?<![a-zäöüß])(?<!als )(?:gewerbe(?!ansiedl|gebiet|betrieb|treib|park|steuer|schein|anmeld)|b[üu]ro(?!stuhl|st[üu]hle|schrank|tisch|m[öo]bel|-?ecke|zimmer)|praxis|souterrain|lagerfl[äa]che|kellergeschoss|ladenlokal|ladenfl[äa]che|ladengesch[äa]ft|einzelhandelsfl[äa]che)"),
    ("pets_forbidden", "pets forbidden",
     "keine (haus)?tiere|keine hunde|haustiere nicht|tierhaltung nicht|no pets|ohne haustiere"),
    ("uninhabitable", "uninhabitable",
     "rohdiamant|entkernt|bastler|ofenheizung|kohleofen|etagenbad|au[ßs]entoilette|ohne (?:bad|heizung)|kein bad"),
]

# ── Negations that switch a gate back off ───────────────────────────────────
NO_WBS     = "wbs\\s*:?\\s*(?:nicht erforderlich|nicht n[öo]tig|nicht notwendig|nein)|kein(?:en)? wbs|ohne wbs|wbs[^.]{0,30}\\bnicht\\s+(?:erw[üu]nscht|m[öo]glich|gew[üu]nscht|akzeptiert|erforderlich)"
NO_FURN    = "un ?m[öo]bliert|nicht m[öo]bliert|ohne m[öo]bel|teilm[öo]bliert|unfurnished"
NO_WG      = "(?:nicht|kein\\w*|nein)[^.]{0,30}\\b(?:wg|wohngemeinschaft\\w*)\\b|\\b(?:wg|wohngemeinschaft\\w*)\\b[^.]{0,30}(?:nicht geeignet|ausgeschlossen|untersagt)|\\bwg[- ]?(?:geeignet|tauglich)\\b|als wg (?:nutzbar|geeignet)"
NO_SUBLET  = "unter(?:zu)?vermiet\\w*[^.]{0,40}(?:nicht|untersagt|ausgeschlossen|verboten)|keine\\s+unter(?:zu)?vermiet|(?:nicht|kein\\w*)[^.]{0,40}unter(?:zu)?vermiet"
NO_SWAP    = "kein(?:e|en)?\\s+(?:wohnungs)?tausch|nicht\\s+(?:zum|zu|im|gegen)\\s+tausch|nicht\\s+(?:ge)?tausch(?:t|en)|no\\s+(?:flat\\s+|apartment\\s+)?(?:swap|exchange)|not\\s+(?:a|for)\\s+(?:swap|exchange)"
# A swap stated this strongly is not cancelled by a negation elsewhere.
SWAP_STRONG = "wohnungsswap|wohnungstausch|tauschwohnung|tauschpartner|tauschangebot|tauschobjekt|nur\\s+tausch|\\btausch\\s*[:!]"

# ── Fixed-term tenancies ────────────────────────────────────────────────────
# Soft signals, plus two date-range forms. A term is often given with no
# keyword at all, just "Available Sep 25 - Nov 11", so a date range counts when
# a word about availability or renting sits next to it. Two full dates with a
# year joined by bis or a dash in the *title* also count: viewing slots and
# opening hours never carry a year.
TEMP_SOFT       = "auf zeit|zeitmietvertrag|(?<!un)befristet|kurzfristig|temporary rental|\\btemporar(?:y|ily)\\b|zeitlich begrenzt|nur f[üu]r einen zeitraum|vor[üu]bergehend|zwischenzeitlich|interim|^[^.]{0,30}\\bbis\\s+\\d{1,2}[.]\\d{1,2}[.]\\d{2,4}|(?:available|verf[üu]gbar|vermietet|frei)\\s*(?:only\\s*)?(?:until|till|bis(?:\\s+zum)?)\\s*\\d{1,2}[./]\\d{1,2}[./]?\\d{0,4}|(?:until|bis)\\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|okt|oct|nov|dez|dec)[a-z]*\\.?\\s*\\d{1,2}|\\d+\\s*[-–]?\\s*month(?:s|ly)?[- ]?(?:contract|period|rental|lease|stay|let\\b)|(?:for|available for)\\s+(?:a\\s+)?(?:period\\s+of\\s+)?\\d+\\s*months?|f[üu]r\\s+\\d+\\s*monate?|auf\\s+\\d+\\s*monate?\\s+(?:vermietet|befristet)"
EXTEND          = "verl[äa]ngerung|verl[äa]ngert werden|option auf verl[äa]ngerung|possibilit\\w* (?:of|to) exten|option to extend|extension (?:is )?possible|extendable|danach unbefristet|[üu]bernahme des mietvertrags m[öo]glich"
DATE_RANGE      = "((?:\\d{1,2}[./]\\d{1,2}(?:[./]\\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|okt|oct|nov|dez|dec)[a-z]*\\.?\\s*\\d{1,2})\\s*(?:-|–|—|bis|to|until)\\s*(?:\\d{1,2}[./]\\d{1,2}(?:[./]\\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|okt|oct|nov|dez|dec)[a-z]*\\.?\\s*\\d{1,2}))"
FULL_DATE_RANGE = "\\d{1,2}\\.\\d{1,2}\\.(?:20)?\\d{2}\\s*(?:bis|[-–])\\s*(?:zum\\s+)?\\d{1,2}\\.\\d{1,2}\\.(?:20)?\\d{2}"

# ── Offer or request ────────────────────────────────────────────────────────
# Kleinanzeigen lets someone post "I am looking for a flat" into the Offers
# category, and the title looks like any other listing ("2 ZKB MIT BALKON").
# Only the body gives it away. OFFER_SIG is checked first, because "Ich suche
# fuer meine Wohnung einen Nachmieter" is an offer, not a request.
#
# provisionsfrei, kaltmiete and besichtigung are deliberately NOT offer signals:
# someone looking for a flat writes exactly those words when stating a budget,
# and one of them was enough to switch the whole gate off.
OFFER_SIG  = "nachmieter|nachmiete\\b|nachmietersuche|zu vermieten|vermietung|wird vermietet|sucht (?:neue[nr]? )?(?:mieter|bewohner|nachmieter)|mieter gesucht|such\\w*\\s+f[üu]r\\s+(?:mein|unser|dies)|sie sind auf der suche|objektreferenz|sucht nette|(?:ich|wir)\\s+such\\w+[^.]{0,40}\\b(?:mieter|nachmieter\\w*|bewohner|familie|p[äa]rchen|paar|person(?:en)?|leute|jemand\\w*)\\b"
GESUCH_SIG = [
    "such\\w*\\s+such\\w*",
    "\\b(?:wir|ich)\\s+such\\w+",
    "(?:ich bin|wir sind|bin|sind)\\s+auf der suche",
    "\\bauf\\s+(?:\\w+\\s+){0,2}(?:wohnungs|zimmer)?suche\\b",
    "wohnungssuche|zimmersuche|suchanzeige|wohnungsgesuch|\\bgesuch\\b",
    "obdachlos|wohnungslos|notunterkunft|obdachlosenheim",
    "alleinerziehend",
    "bitte um hilfe|bitte helft|ich flehe|dringlichkeitsschein|sonderwohnbedarf",
    "\\bhousing request\\b|\\b(?:flat|house|apartment|room)[- ]?hunt(?:ing)?\\b",
    "\\blooking for (?:a |an |some |the |our )?(?:new |nice |small |cozy |quiet |long[- ]term |mid[- ]term |shared |furnished |rental )*(?:\\d[- ]?(?:room|zimmer)[- ]?)?(?:home|flat|apartment|appartment|room|place|studio|rental|accommodation|accomodation|housing|lease|wohnung|zimmer|bleibe)\\b",
    "\\bsearching for (?:a |an |some )?(?:new )?(?:flat|apartment|room|place|home|studio|rental|accommodation)\\b",
    "\\bin search of (?:a |an )?(?:flat|apartment|room|place|home|studio)\\b",
    "\\b(?:i|we) (?:urgently |really )?need (?:to find )?(?:a |an )?(?:new )?(?:place|flat|apartment|room|home|studio)\\b",
]

# ── Features ────────────────────────────────────────────────────────────────
#
# English name to German pattern, because the listings are in German and the
# person filling in the profile is not. `home.wants` and `home.deal_breakers`
# are matched through here, so somebody can type "balcony" and still match
# "Loggia" and "Dachterrasse".
#
# `points` is the default weight. The profile can override any of them, and
# anything it does not mention scores nothing.
#
# Keep these small. A bonus is a tie-breaker between two flats that are
# otherwise equal, not a way to lift an inconvenient flat into the shortlist.
# Fitted kitchen is worth 2 rather than 10 for exactly that reason: Fredy
# truncates descriptions, so a generous bonus here ends up going to everyone.

# Alternative spellings accepted from a profile, so nobody has to guess which
# word this code happens to use.
ALIASES = {"lift": "elevator", "balcon": "balcony", "bath tub": "bathtub",
           "bath": "bathtub", "kitchen": "fitted kitchen",
           "einbaukueche": "fitted kitchen", "ebk": "fitted kitchen"}

FEATURES = {
    "balcony":        dict(rx="balkon|loggia|dachterrasse|terrasse", points=4, show="balcony"),
    "bathtub":        dict(rx="badewanne|\\bwanne\\b", points=4, show="bathtub"),
    "elevator":       dict(rx="aufzug|fahrstuhl|\\bpersonenaufzug|\\blift\\b", points=2, show="elevator"),
    "fitted kitchen": dict(rx="einbauk[üu]che|\\bebk\\b|k[üu]chenzeile|wohnk[üu]che|offene k[üu]che", points=2, show="kitchen mentioned"),
    "unlimited contract": dict(
        rx="(?<!be)unbefristet", points=2, show="unlimited contract",
        note="The lookbehind matters: befristet is the opposite and contains the word."),
    "furnished":      dict(rx="(?<!un)m[öo]bliert|furnished|voll ?m[öo]bl|m[öo]bliertes wohnen", points=-6, show="furnished",
                           note="Negative by default, flip the sign if you want it."),
    "loft bed":       dict(rx="hochbett|schlafempore|schlafgalerie|schlafebene|\\bempore\\b", points=-8, show="bed on a mezzanine"),
    "needs work":     dict(rx="renovierungsbed|sanierungsbed|renoviere\\b|gestaltungspotenzial|viel potenzial|handwerker|bezugsfertig nach|malerarbeiten", points=0, show="needs renovation",
                           note="Scores nothing on purpose. It is a flag and a lever "
                                "on the price, and whether it is bad depends on the person."),
}

# A flat with a shower and no bathtub, when the profile asks for a bathtub.
SHOWER_ONLY = ("dusche|duschbad|duschkabine|\\bshower\\b", "badewanne|wannenbad|(?<![a-zäöüß])wanne\\b|\\bbathtub|\\bbath\\s*tub|\\btub\\b|\\bbad\\s+mit\\s+wanne|\\bmit\\s+(?:einer\\s+)?wanne")


def hard_hits(text, title=None, gate_pets=False):
    """Ids of the hard gates this listing trips. Empty list means it passed.

    `title` is passed separately because two checks are anchored to it: a
    garage or storage unit names itself in the title, while in the body those
    words almost always mean "a parking space comes with the flat", which is a
    plus rather than a rejection.
    """
    t = (text or "").lower()
    hits = [i for i, _label, rx in HARD if re.search(rx, t)]

    if not gate_pets and "pets_forbidden" in hits:
        hits.remove("pets_forbidden")
    if title and re.search("\b(garage|stellplatz|tiefgarage|duplexparker|carport|"
                           "lagerraum|abstellplatz)\b", title, re.I) \
            and "not_residential" not in hits:
        hits.append("not_residential")
    if "wbs" in hits and re.search(NO_WBS, t):
        hits.remove("wbs")
    # A flatshare gate is only lifted when the listing is not the room itself.
    if ("flatshare_or_room" in hits and re.search(NO_WG, t)
            and not re.search("wg-?zimmer|zimmer in |mitbewohner|untermieter gesucht", t)):
        hits.remove("flatshare_or_room")
    # Zwischenmiete, Ferienwohnung and Boardinghouse are not rescued by a negation.
    if "sublet_or_hotel" in hits and re.search(NO_SUBLET, t) and not re.search(
            "zwischenmiete|ferienwohn|monteur|boardinghouse|apartmenthaus|serviced|"
            "zeitwohnen|kurzzeit|short.?term|sublet", t):
        hits.remove("sublet_or_hotel")
    if ("swap_not_rental" in hits and re.search(NO_SWAP, t)
            and not re.search(SWAP_STRONG, t)):
        hits.remove("swap_not_rental")

    if re.search(TEMP_SOFT, t):
        hits.append("fixed_term")
    elif re.search("(?:available|verf[üu]gbar|frei|vermietet|miete|rental|stay)[^.]{0,40}"
                   + DATE_RANGE, t, re.I):
        hits.append("fixed_term")
    elif ((title and re.search(FULL_DATE_RANGE, title))
          or re.search("\b(?:vom|ab)\s+" + FULL_DATE_RANGE, t, re.I)) \
            and not re.search(EXTEND, t):
        hits.append("fixed_term")
    return hits


def is_request(text):
    """True when somebody is looking for a flat rather than offering one."""
    t = (text or "").lower()
    if re.search(OFFER_SIG, t):
        return False
    return any(re.search(rx, t) for rx in GESUCH_SIG)


def features(text, wanted=None, avoided=None):
    """(points, flags) from the feature table, limited to what the profile named."""
    t = (text or "").lower()
    pts, flags = 0.0, []
    norm = lambda xs: {ALIASES.get(n.strip().lower(), n.strip().lower()) for n in (xs or [])}
    wanted_n, avoided_n = norm(wanted), norm(avoided)
    names = wanted_n | avoided_n
    for name, f in FEATURES.items():
        if names and name not in names:
            continue
        if re.search(f["rx"], t):
            p = float(f["points"])
            if name in avoided_n:
                p = -abs(p)
            pts += p
            if f.get("show"):
                flags.append(f["show"])
    return pts, flags


LABELS = {i: label for i, label, _ in HARD}
LABELS["fixed_term"] = "fixed-term tenancy"
LABELS["shower_only"] = "shower only, no bathtub"
LABELS["template_title"] = "template title, not a real listing"
