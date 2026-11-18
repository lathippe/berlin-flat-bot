# Flat HQ

The board for the flats you are actually considering. The map of Berlin fills the
screen, every flat sits on its address with its score and warm rent, and the
cards run down the right. Click a point and its card opens; open a card and the
map shows the trip to the office in BVG line colours.

It opens with two example flats. Remove them under **data** at the top.

## Open it

Double-click `index.html`. Everything works from the file except reading your
profile automatically. For that, serve the repo root:

```sh
python3 -m http.server 8000      # from the repo root, not from dashboard/
open http://localhost:8000/dashboard/
```

Served this way the board reads `../profile.json`, the file the interview
wrote. Opened as a file, load it once with **profile** at the top; the browser
remembers it.


## Your office

Every commute is measured to one place. The board takes it from the first
entry in `anchors` of your `profile.json` that has coordinates:

```json
"anchors": [{ "id": "office", "label": "Office", "lat": 52.5219, "lng": 13.4132, "max_minutes": 40 }]
```

Until you set one, the board uses Alexanderplatz as a stand-in, and the two
example flats are routed there. Reload the page after loading a new profile.

## Where the score comes from

Your bot profile. The interview rated nine factors from 0 to 5; the board turns
the ratings into 100 points and scores each flat out of 10 on them. A factor
you rated 0 is left out. The colours: emerald from 7.5, blue from 5 to 7.5, red
under 5. Each card lists its pluses and minuses against your limits and
must-haves, then your own notes below them.

Two factors are your judgement, not data: how much you like the area and what
you need nearby. You rate both from 1 to 5 when you add a flat.

## Add a flat

**add flat** at the top. Type the address and press **Find the address and the
trip to the office**: it geocodes on OpenStreetMap and measures the weekday
08:30 trip to your office on transitous.org, with the route
the map draws. If either service is unreachable, type the minutes yourself.

Flats you add are kept in this browser. **data** copies them out as JSON, and
imports a backup on another computer. To make flats permanent, paste them into
`flats.js`.

### Fields

Same as the form. The ones the board reads:

| field | what |
| --- | --- |
| `id` | unique, letters and dashes |
| `name`, `short`, `who` | address and area, short label, landlord or portal |
| `stage` | `wrote`, `arranging`, `viewing`, `waiting`, `deciding`, `backup`, `archive` |
| `seen`, `viewing` | viewed in person; viewing date `2026-11-24T18:00` |
| `warm`, `kalt`, `size`, `rooms` | euros, m², rooms |
| `floor`, `lift`, `balcony`, `kitchen`, `bathtub` | text, then true or false |
| `free`, `term`, `deposit`, `anmeldung`, `pets` | move-in, contract, money up front, `yes`/`no`, `allowed`/`ask`/`no` |
| `transit`, `office`, `route` | `Station · lines · N min walk`, minutes to the office, the route the lookup fills |
| `lat`, `lng` | coordinates |
| `areaRate`, `nearRate` | your 1 to 5 ratings |
| `verdict`, `status`, `pros`, `cons`, `photos`, `link` | your notes, links |
| `plan3d` | `plan3d.html?f=<file name>` |

## 3D plans

`plan3d.html?f=boxhagener` opens a plan in 3D with the sun moving through it on
any date. Each plan is one file in `plan3d/`. To add yours, copy
`plan3d/boxhagener.js`, rename it and the key inside, and redraw it from the
listing's floor plan: 1 plan pixel is 1 cm, walls are drawn from corner to
corner, and openings are given in metres along the wall. Set `north` and the
`facades` so the sun panel says which rooms get direct light and when. Then
put `plan3d: "plan3d.html?f=<name>"` on the flat.

## Files

```
index.html          the board
map.html            the map, also used inside the board
plan3d.html         3D plan engine; plans in plan3d/
flats.js            your flats (starts with two examples)
store.js            flats, profile and the score, shared by all pages
header.js           top bar
data/berlin-geo.js  districts, LOR areas, parks, Spree, S-Bahn ring, neighbourhood stats
```

Data: Geoportal Berlin and Amt für Statistik Berlin-Brandenburg (dl-de/by-2-0),
OpenStreetMap contributors (ODbL), map tiles at close zoom from Esri, routing
by transitous.org.
