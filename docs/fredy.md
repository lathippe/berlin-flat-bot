# Fredy

[Fredy](https://github.com/orangecoding/fredy) is a separate scraper that
watches listing portals. This repo does not replace it: Fredy finds listings,
this bot decides which of them are worth your evening.

**Worth knowing before building anything on top.** Fredy is Apache-2.0 with a
Commons Clause attached, which its own README describes as source-available
rather than open source. You may run it, modify it and share it. You may not
sell it, or sell something whose value comes substantially from it. Personal
use is entirely fine; a commercial product that depends on Fredy is not, and
would need its own scrapers instead.

Nothing else here depends on Fredy. The listing language, scoring, profile,
neighbourhood and nearby modules all work from a row of data, wherever it came
from. Only `fredy/providers/` is written against Fredy's internals.

## Running it

```sh
docker run -d --name fredy -p 9998:9998 \
  -v ~/fredy/conf:/conf -v ~/fredy/db:/db \
  ghcr.io/orangecoding/fredy:latest
```

Open `http://localhost:9998`. Jobs are created in that web UI and stored in its
own SQLite database, not in a config file in this repo.

## Custom providers

`fredy/providers/` holds scrapers for Berlin's municipal housing companies,
which are where the affordable flats actually are and which Fredy does not ship
with:

| File | Company |
| --- | --- |
| `gewobag.js` | Gewobag |
| `degewo.js` | degewo |
| `howoge.js` | HOWOGE |
| `vonovia.js` | Vonovia |
| `buwog.js` | BUWOG |
| `never-areas.js` | shared area filter, not a provider |

Copy them into Fredy's `lib/provider/` and rebuild its image. Each file's
header comment records how that site had to be scraped and when it was last
verified, because these sites change and a silently empty provider looks exactly
like a quiet market.

## never-areas.js is generated

`areas.never` in your profile is the source of truth. Fredy needs its own copy
because it filters while scraping and never sees this repo, so:

```sh
python3 fredy/sync-never-areas.py     # after every change to areas.never
```

That rewrites `fredy/providers/never-areas.js`, and then Fredy's image has to be
rebuilt for it to take effect. Do not edit the file directly; it says so at the
top and the next sync will overwrite you.

The two lists existing separately is not an accident: Fredy only sees a
listing's title and description at scrape time, while the district usually
lives in the address. Filtering there saves fetching pages this bot would
discard anyway. Keeping them in step by hand, though, is a standing invitation
to a silent bug, which is why it is a script.

## Setting up a job

One job per portal. In the UI:

- **Provider**: pick one, or one of the custom ones above.
- **URL**: the portal's own search results page with your filters already
  applied. Open the portal, search by hand until the results look right, copy
  the URL. Gewobag in particular returns only an empty form without filter
  parameters in the query string.
- **Notification adapter**: none needed. The bot reads Fredy's database
  directly (`src/watch.py`).
- **Blacklist**: leave it mostly empty. The gates in `docs/card.md` do this
  job better, and a word list here cannot see the address.

Check each job once after creating it. A provider that returns zero results
forever is the most common failure, and it is invisible unless you look.
