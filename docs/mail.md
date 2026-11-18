# Connecting your mailbox

Once you start applying, the portals answer by email. The mail watcher reads
that mailbox and turns it into Telegram messages, so viewing invitations do not
sit unread between newsletters.

It needs read access to your Gmail, plus the right to label and archive if you
let it tidy up.

## What it does

- Finds housing mail: known portal domains, plus subject and body matching for
  `Wohnung`, `Besichtigung`, `Objekt`, `Exposé`, `Selbstauskunft`.
- Pushes anything time-critical to Telegram immediately. **A viewing invitation
  with a date and an address is the one message that must never wait**, so it
  goes out first and on its own.
- Records which flats you have applied to, in a store shared with the listing
  gates. A flat you already wrote to is never sent to you again as if it were
  new.
- Optionally labels and archives what it has processed.

## Getting credentials

The watcher talks to the Gmail API directly. You need an OAuth client of your
own; there is no shared one, and there should not be.

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create a
   project.
2. **APIs & Services → Library → Gmail API → Enable.**
3. **OAuth consent screen**: External, add your own address as a test user.
   Leave it in testing mode. It does not need review for personal use.
4. **Credentials → Create credentials → OAuth client ID → Desktop app.**
   Download the JSON.
5. Save it and run the one-time consent:

   ```sh
   mkdir -p ~/.config/berlin-flat-bot
   mv ~/Downloads/client_secret_*.json ~/.config/berlin-flat-bot/oauth.json
   python3 src/mail_auth.py
   ```

   A browser opens, you approve, and a refresh token is written next to it.
   That token is what the watcher uses from then on.

Scope: `gmail.modify`. Read alone is not enough if you want labelling and
archiving; drop to `gmail.readonly` if you would rather it never touch
anything, and run with `--no-label --no-archive`.

## Running it

```sh
python3 src/mail_watch.py --dry          # print what it would send, send nothing
python3 src/mail_watch.py --since=7d     # look further back than the default
python3 src/mail_watch.py                # for real
```

Start with `--dry` for a few days. It is the component most likely to be either
too chatty or too quiet, and that is cheap to find out before it is on a timer.

## Keep in mind

- **The token is yours.** `~/.config/berlin-flat-bot/` is in `.gitignore` and
  must stay out of the repo.
- **Testing-mode refresh tokens expire after seven days** while the consent
  screen is unverified. If the watcher starts failing to authenticate about a
  week in, that is why: either re-run `mail_auth.py` or publish the consent
  screen, which for a single-user desktop app needs no review.
- A mailbox with years of history makes the first run slow. `--since=2d` is the
  default for that reason.
