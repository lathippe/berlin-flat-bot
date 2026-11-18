# Setup, in order

Allow about an hour, most of it waiting for Google.

## 1. Your profile

```sh
python3 data/fetch.py            # Berlin nursery and school registers
python3 intake/interview.py      # ~10 minutes of questions
```

The interview writes `profile.json` in the repo root. It is git-ignored and it
is the only file with opinions in it. Re-run it whenever something changes;
your stored answers come back as the defaults.

Check the result before moving on. The two things worth re-reading are
`areas.never`, which is easy to make broader than you meant, and `anchors`,
where a wrong geocode puts your office two streets away and quietly reshapes
every result.

## 2. Telegram

Full version in [card.md](card.md). Short version:

```sh
printf '%s' '<token from @BotFather>' > ~/.flatbot_token
chmod 600 ~/.flatbot_token
```

Your chat id comes from @userinfobot and goes in the profile. Send your bot a
message by hand first, or it cannot message you.

Then check it works end to end:

```sh
python3 src/places.py 52.4886 13.4253    # should print your nearby lines
```

## 3. Fredy

[fredy.md](fredy.md). Install it, create one job per portal, point the
notification webhook at this bot. Then:

```sh
python3 fredy/sync-never-areas.py
```

and rebuild Fredy's image so it picks up your area list.

Verify each job returns something the day you create it. A provider that
silently returns zero results forever is the most common failure here and it
looks exactly like a quiet market.

## 4. Mail

[mail.md](mail.md). This is the slow one: a Google Cloud project, the Gmail API
enabled, an OAuth client, and a consent screen left in testing mode.

Run it with `--dry` for the first few days.

> In testing mode the refresh token expires after seven days. If authentication
> starts failing about a week in, that is why.

## 5. On a timer

Once each piece works by hand, put it on a schedule. On macOS that is launchd;
on Linux, cron or a systemd timer. Ten to fifteen minutes between runs is
plenty: the portals do not publish faster than that, and the gates are cheap
but the routing calls are not.

Two things that will bite you on macOS specifically:

- **launchd cannot read iCloud Drive.** If you keep the repo in iCloud, copy
  the working files somewhere local and run from there. A scheduled job that
  works by hand and silently never fires is almost always this.
- **Full Disk Access.** A scheduled job needs it before it can read anything
  interesting.

## When something stops working

In rough order of likelihood:

1. A Fredy job returning nothing because the portal changed its markup. Check
   the job in Fredy's UI first, it is the single most common cause.
2. Gmail auth expired, see above.
3. Overpass mirrors all down. Lines say *not measured*; nothing is rejected
   because of it, and it fixes itself.
4. `areas.never` broader than intended after an edit. Everything gets dropped
   and it looks like no flats exist.
