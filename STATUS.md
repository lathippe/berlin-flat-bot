# What runs today

This repo is a working flat bot being assembled out of a single-user original.
The decision layer is done and tested. The delivery layer, the part that
actually pulls listings in and posts them to Telegram, is not finished.

Read this before you spend an evening on it.

## Works, and was tested

| | |
| --- | --- |
| `data/fetch.py` | Downloads both Berlin registers. 2 905 nurseries, 930 schools. |
| `intake/interview.py` | Full interview, writes a valid `profile.json`. Re-runnable as an editor. |
| `src/listings.py` | What a German listing is saying: 10 hard gates, their negations, fixed-term detection, offer-versus-request, the feature table. **Verified against the original implementation, 21 of 21 identical**, including every false-positive case. |
| `tests/test_listings.py` | 27 assertions over the above. Run it after touching any pattern. |
| `src/profile.py` | Loads the profile, fills defaults, warns about the mistakes that quietly produce an empty inbox. |
| `src/scoring.py` | The score out of 100, entirely profile-driven. |
| `src/watch.py` | The loop. Reads Fredy's database, runs every listing through the gates, renders and sends what survives, and prints why the rest were dropped. **Exercised against a real Fredy database of 1 269 active listings.** |
| `src/pipeline.py` | The gates in order, cheapest first. Every rejection carries a category so a run can be tallied. |
| `src/state.py` | What was seen, sent, turned down and applied to. Identity is the flat, not the link. |
| `check-address.py` | One address through everything, no tokens needed. |
| `src/notify.py` | Delivery to Telegram, email or WhatsApp. All three verified structurally: Telegram and Twilio reach their APIs and return a clean 401 with a deliberately wrong token, which proves URL, parameters and encoding; email builds the message and reaches SMTP. Failures explain what to fix rather than raising a traceback. **No channel has delivered a real message yet, because that needs a real token.** |
| `src/kiez.py` | The neighbourhood block, from Berlin's LOR statistics for 543 planning areas. |
| `src/card.py` | Renders the message. Verified end to end on a real Berlin address. |
| `src/transit.py` | Tier at the door and door-to-door minutes to every anchor, against the live router. |
| `src/places.py` | Measures everything in `profile.nearby`. Verified on a real address: 75 nurseries within 1 km, 12 primary schools within 1.5 km. |
| `fredy/sync-never-areas.py` | Generates the Fredy area filter from your profile. |
| `dashboard/` | The flat board: map, cards, comparison, 3D plans. Opens with two example flats. |
| `src/mail_auth.py` | Runs and fails with the right message when no OAuth client is present. The browser consent round trip has **not** been run end to end. |

## Ported but not re-verified

`fredy/providers/*.js` — five scrapers for Berlin's municipal housing
companies, comments translated. They were last verified against the live sites
in late September 2026. Portals change their markup; assume at least one needs
a fix. Check each job returns something the day you create it.

## Not here yet

| | |
| --- | --- |
| `src/mail_watch.py` | The Gmail reader. `mail_auth.py` prepares its credentials; the watcher itself is not ported. |
| Portal watchers | ImmoScout, Kleinanzeigen, Wunderflats, the Telegram channel listener. |

So: the loop works, and a clean clone was verified end to end on Python 3.9:
37 files, 2 MB, tests pass, the interview produces a valid profile, and every
module imports. What is missing is the mail watcher, the sources beyond Fredy,
and one real delivered message.

## What you can usefully do now

Run the interview and read your `profile.json`. That file is the whole design:
if the answers in it are wrong, nothing built on top will be right. Then
`python3 src/places.py <lat> <lng>` on an address you know to see whether the
nearby lines match your own sense of the area. Both are worth doing before any
of the rest lands.
