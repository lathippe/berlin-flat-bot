# What "nearby" can and cannot tell you

Every entry in `profile.nearby` produces a line on every listing the bot sends.
The lines look alike. The claims behind them are not equally strong, so this
page says plainly what each source knows.

## The sources

| `source` | What it is | Trust |
| --- | --- | --- |
| `berlin-kita` | Berlin's official nursery register, 2 905 entries | High |
| `berlin-school` | Berlin's official school register, 930 entries | High |
| `overpass` | OpenStreetMap, queried live | Varies, read below |
| `manual` | Written down in your profile, nothing measuring it | None |

Both registers ship in `data/` and are refreshed with `python3 data/fetch.py`.
They come from `gdi.berlin.de` under Datenlizenz Deutschland 2.0.

## The official registers

These are the real thing: every licensed nursery and every school in Berlin,
with coordinates, from the Senate department that licenses them.

What they still do not tell you:

- **Nurseries have no free places in the data.** `e_platz` is the licensed
  capacity, not a vacancy. Fifteen nurseries within walking distance is good
  news about the area and no news at all about getting a place in one.
- **School catchments are not modelled.** The bot measures distance. Berlin
  assigns primary school places by `Einschulungsbereich`, and the nearest
  school is often not the one you are assigned. Treat the count as "this is a
  neighbourhood with schools in it", then check the catchment yourself for any
  flat you are serious about.
- `kind` distinguishes a Kindertagesstätte from a parent initiative
  (`Eltern-Initiativ-Kindertagesstätte`, 565 of them) and a forest kindergarten.
  Filter on it if that matters to you: `"query": {"kind": "Eltern-Initiativ"}`.

## OpenStreetMap, through Overpass

Good for things that are physically on a street and that somebody bothered to
map: playgrounds, parks, supermarkets, gyms, doctors, places of worship. Berlin
coverage is dense.

Three things to know:

1. **The public servers fail often.** Roughly half the test queries returned
   504 during development. `src/places.py` tries three mirrors and caches every
   answer for 30 days. When all three refuse, the card says *not measured*
   rather than *none*, because a server outage must never read as an empty
   neighbourhood.
2. **Name matching is a trap.** The first version of the Indian-community query
   searched shop names for `desi` and matched three design studios, because
   `desi` is inside `design`. Every name pattern in this repo is wrapped in
   `\b` word boundaries for that reason. If you add one, test it before you
   trust it.
3. **Tag coverage is uneven.** `cuisine=indian` is well maintained.
   `amenity=school` is not: it catches private institutes, language schools and
   a Quranic centre. That is exactly why schools come from the official
   register instead.

## Community proximity: read this before using it

`indian_community` and `turkish_community` are **proxies, and they measure
infrastructure, not people.**

What the query actually counts: Indian restaurants, Indian grocers, and Hindu
or Sikh places of worship within the radius. On a test address it returns 37, the
closest 129 m away, naming Sri Ganesha Hindu Tempel and Vinayaka Bhavan. That
is a real signal, and it is genuinely useful: those are the places you would
actually go.

What it does **not** measure is where Indian families live. A neighbourhood can
have a large Indian population and few Indian businesses, or a popular
restaurant strip and almost no Indian residents. No official Berlin dataset
breaks residents down by country of origin at neighbourhood level in a form
this bot reads today.

**The honest upgrade** if this matters a lot: the Amt für Statistik
Berlin-Brandenburg publishes resident counts by nationality per planning area
(`Einwohnerregisterstatistik`, by LOR). Wiring that in would turn the proxy into
a measurement. It is not done here. Treat the current number as "is there
community infrastructure around" and nothing more.

## Adding your own

```json
{
  "id": "swimming",
  "label": "Swimming pool",
  "source": "overpass",
  "query": "nwr[\"leisure\"=\"sports_centre\"][\"sport\"=\"swimming\"]",
  "radius_m": 2000,
  "want": "any",
  "weight": 4
}
```

- `want`: `any` rewards the first one found, `many` rewards density and
  saturates at five, `none` rewards the absence of something.
- `weight`: points out of 100. Keep the whole `nearby` block under about 25
  or it starts outvoting rent and commute.
- `min_count`: makes it a filter instead of a preference. Use sparingly. An
  entry that could not be measured never rejects a flat.
- `show_label`: set it to `false` and the card line leads with the places
  rather than the category. The community entries default to this. Somebody
  who asked to be near their own community does not need a label repeating it
  back at them in every message; what they cannot get anywhere else is which
  temple, which grocer, and how far:

  ```
  · Avatar, Vinayaka Bhavan, Sri Ganesha Hindu Tempel — 44 within 3 km, closest 129 m
  ```

Several selectors can share one entry: separate them with `;` and each is
counted. The `(around:)` filter is appended by the code, so you cannot forget
it and accidentally query the planet.
