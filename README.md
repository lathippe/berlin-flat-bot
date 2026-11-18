# berlin-flat-bot

A flat hunt in Berlin is a race you lose by being slower than someone who is
refreshing a portal at 11pm. This watches the portals for you, throws away what
you would have thrown away, and sends you the rest on Telegram with enough on
the card to decide without opening it.

It was built for one person's search in 2026 and then taken apart so the
criteria live in a file instead of in the code. Yours go in `profile.json` and
nothing else has an opinion.

It is built on top of [Fredy](https://github.com/orangecoding/fredy), a free
scraper that watches the listing portals. Fredy finds the listings; this repo
decides which of them are worth your evening and writes the card. You run
Fredy yourself, `docs/fredy.md` covers how, and its licence forbids selling it
or anything that substantially depends on it.

## What a listing has to survive

Sixteen gates, cheapest first: duplicates, bait prices, scam patterns, wanted
ads posing as offers, your deal-breaker phrases, areas you ruled out, a real
door-to-door transport route to every place you need to reach, whatever you
said has to be nearby, and the rent ceiling. What is left gets scored out of
100 and sorted. `docs/card.md` lists them in order.

A gate that cannot be evaluated never rejects. If a server is down the card
says *not measured*, because an outage must not read as a bad neighbourhood.

## What is on the card

Address, rent warm and cold and per m², the nearest station with the lines and
the walking minutes, travel time to each of your anchors, and a neighbourhood
block from Berlin's LOR statistics: who lives there by age, social status and
whether it is rising or falling, how many people stay five years or more, crime
relative to the city average, noise, greenery.

Then one line per thing you said should be nearby. Nurseries and schools come
from Berlin's official registers, 2 905 and 930 entries, shipped in `data/`.
Everything else is OpenStreetMap. The card says which, because those are
different classes of claim. `docs/nearby.md` is blunt about what each source
can and cannot tell you, and about which entries are proxies rather than
measurements.

> **Partly built.** The interview, the profile, the gates, the scoring and the
> loop over Fredy's database work and are tested. So does the flat board in
> `dashboard/`. The mail reader and the portal watchers beyond Fredy are not
> here yet.
> [STATUS.md](STATUS.md) is specific about which is which.

## Start here

```sh
python3 data/fetch.py            # Berlin nursery and school registers, once
python3 intake/interview.py      # it asks, you answer, profile.json appears
```

The interview takes about ten minutes. It ends with an open question, because
the fixed ones will miss whatever matters to you specifically, and before that
it asks what actually decides it for you and divides the 100 points accordingly.

That part is not decoration. Rate being central at zero and it is dropped from
the scoring outright, rather than kept at some small weight you never chose.
Two profiles over the same two flats, one built for somebody who wants space
and does not mind the outskirts, the other for somebody who wants to be in the
middle of town:

| | space, far is fine | central |
| --- | --- | --- |
| 98 m², 4 rooms, outer Pankow | **81** | 57 |
| 52 m², 2 rooms, Mitte | 47 | **59** |

Same listings, opposite order. Then `docs/setup.md`, which is the rest in
order: Telegram bot, Fredy, mail.

Re-run the interview any time. Your stored answers become the defaults, so it
doubles as the editor.

## The flat board

`dashboard/` is a page for the flats you are actually considering: a map of
Berlin with every flat on it, a card per flat scored on your priorities, the
trip to your office drawn in BVG line colours, a side-by-side comparison, and
a 3D walk-through of a floor plan with the sun moving through it. It works
without the bot. Open `dashboard/index.html`, or serve the repo root so the
board picks up your `profile.json` by itself:

```sh
python3 -m http.server 8000     # then open http://localhost:8000/dashboard/
```

It opens with two example flats. `dashboard/README.md` explains how to add
yours, set your office and draw a plan.

## Layout

```
profile.json          yours, git-ignored. Everything the bot believes.
profile.schema.json   what may go in it, with the reasoning
intake/interview.py   the questions
src/places.py         what is near a flat
data/fetch.py         downloads the Berlin registers
data/kiez-lor.json    neighbourhood statistics, 543 planning areas
fredy/providers/      scrapers for Berlin's municipal housing companies
docs/                 setup, telegram, fredy, mail, nearby
dashboard/            the flat board: map, cards, comparison, 3D plans
```

## Licence

MIT for the code in this repository, see `LICENSE`. Fredy is a separate project
under its own licence, which forbids selling it or anything that substantially
depends on it. The data in `data/` keeps the licences listed below.

## Data sources

Attribution these datasets require, and who to thank:

- Neighbourhood statistics, nursery and school registers: Geoportal Berlin,
  under Datenlizenz Deutschland Namensnennung 2.0.
- Points of interest: OpenStreetMap contributors, under ODbL.
- Routing: [transitous](https://transitous.org), a free public MOTIS instance.
- Geocoding: Nominatim. One request per second. Please leave it that way.

[Fredy](https://github.com/orangecoding/fredy) is a separate project and is not
included here. `fredy/providers/` holds extra scrapers that plug into it.
