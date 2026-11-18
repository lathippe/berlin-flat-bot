# The card, and what it takes to earn one

Delivery is a separate question: Telegram, email or WhatsApp, set in the
interview and explained in [delivery.md](delivery.md). This page is about
what is in the message and why the listing survived to be sent at all.

## What a card looks like

One message per listing that survives the gates. The card is built so you can
decide without opening the listing:

```
🟢 Friedrichshain · 78 · Example Straße 1
📍 10245 · 4.1 km from the centre
🚇 U Frankfurter Tor · U5 · 6 min walk
💰 1 480 € warm · 1 150 € kalt · 14.7 €/m²
🧭 office 24 min · school run 11 min
📐 82 m² · 3 rooms
🏘 Boxhagener Platz · Friedrichshain · 18 400 residents
👥 mostly 27–45, 41 % · under 18 24 · 18–27 14
🟢 social status high, stable
🔴 crime above average, ×1.4
🟢 quiet · green space available
· Nursery / Kita: 14 within 1000 m, closest 180 m (official register)
· Primary school: 4 within 1500 m, closest 310 m (official register)
· Playground: 6 within 800 m, closest 120 m
✅ balcony · lift
⚠️ above your comfortable level by 80 €
```

Which blocks appear is controlled by `profile.report`. Lines that are not
yours never appear: with no pet in the profile the card never tells you to
check a pet policy, because a field that is never relevant teaches you to skip
the whole field.

Which blocks appear is also controlled by `profile.report`. The neighbourhood block
comes from Berlin's LOR statistics in `data/kiez-lor.json`, covering 543
planning areas: age mix, social status and its trend, how many residents have
lived there five years or more, a crime index relative to the city average,
noise and greenery.

## The gates, in the order they run

A listing has to pass all of these. The first failure stops the work, so the
cheap checks come first and the ones that cost a network call come last.

| # | Gate | Driven by |
| --- | --- | --- |
| 1 | Seen before, or already applied to | local state |
| 2 | Duplicate of a flat already sent, matched on postcode, street, number and size rather than on the link | local state |
| 3 | Price is not a monthly rent (bait listings quoting a weekly or total figure) | built in |
| 4 | Listing already taken down | portal |
| 5 | Scam signals: seller account created the same day, a different city in the text, a title already banned | built in |
| 6 | Deal-breaker phrases in title or description | `home.deal_breakers` |
| 7 | It is a *wanted* ad, not an offer | built in |
| 8 | Pets forbidden | `person.pets` |
| 9 | Address will not geocode | built in |
| 10 | Area on the never list | `areas.never` |
| 11 | Too far from the centre in a straight line | `areas.max_km_center` |
| 12 | No public transport route, or longer than allowed, to any anchor | `anchors[].max_minutes` |
| 13 | Only reachable by a mode you do not count | `transit.modes` |
| 14 | Too few of something you required nearby | `nearby[].min_count` |
| 15 | Over the rent ceiling | `budget.max_warm`, `budget.stretch_*` |
| 16 | Score below the floor | `MIN_SCORE` |

Two deliberate choices worth knowing:

- **A gate that cannot be evaluated does not reject.** If Overpass is down or
  the router times out, the card says *not measured*. A flat is never dropped
  because a server was unavailable.
- **Bus-only addresses.** If `transit.modes` leaves out `bus`, an address
  reachable only by bus is rejected even when the bus is fast. That is a
  preference, and it is yours to set: put `bus` in the list and it stops being
  a gate.

## Tuning it

If the bot sends too much, raise `min_score` before you start tightening
gates: gates remove whole categories, the score just reorders. If it sends too
little, the usual culprits are `areas.never` being broader than you meant and
`transit.max_walk_min` being too strict.

If it sends the wrong things, that is usually `weights`, not the gates. Re-run
the interview and redo the priorities section; your previous ratings come back
as the defaults so you are adjusting rather than starting over.

Everything is in `profile.json`. Re-run `python3 intake/interview.py` to walk
through the questions again with your current answers as defaults.
