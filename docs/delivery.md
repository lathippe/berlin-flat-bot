# Where the bot reaches you

Pick once, in the interview. Change it by re-running `intake/interview.py`.

The three are not equally good for this job, and the differences are not
cosmetic.

| | Setup | Carries the full card | Speed you notice it | Cost |
| --- | --- | --- | --- | --- |
| Telegram | 2 minutes | yes, with a map | immediate | free |
| Email | 10 minutes | yes | slower | free |
| WhatsApp | 30 minutes, with a catch | partly | immediate | per message |

## Telegram

The best fit, and the least work.

1. Message **@BotFather**, send `/newbot`, pick a name. It replies with a token.

   ```sh
   mkdir -p ~/.config/berlin-flat-bot
   printf '%s' '8123456789:AAH...' > ~/.config/berlin-flat-bot/telegram_token
   chmod 600 ~/.config/berlin-flat-bot/telegram_token
   ```

2. Message **@userinfobot** for your numeric id. The interview asks for it.
3. **Open a chat with your own bot and send it anything.** A bot cannot message
   you until you have spoken to it once. This is the step everybody misses.

## Email

The most portable option, and the one that puts the alerts next to the replies
from landlords. The trade is that you notice an email in an hour and a push
notification in a minute, which in this market is the difference between a
viewing and a waiting list.

Two ways in, and the first avoids a second secret:

**Through Gmail**, reusing the credentials the mail watcher already needs. Run
`python3 src/mail_auth.py` once (see [mail.md](mail.md)) and leave the SMTP
fields empty. The bot sends from your own address to your own address.

**Through any SMTP server.** The interview asks for host, port and username.
The password goes in a file, never in the profile:

```sh
printf '%s' 'your-app-password' > ~/.config/berlin-flat-bot/smtp_password
chmod 600 ~/.config/berlin-flat-bot/smtp_password
```

For Gmail over SMTP that has to be an App Password, not your account password,
and App Passwords need two-factor authentication switched on first.

## WhatsApp

Workable, and the most trouble. Know what you are agreeing to before you pick
it.

**Meta does not allow unsolicited business messages.** A business number may
message you freely only inside a 24-hour window that opens when *you* write to
it. Outside that window, only pre-approved message templates are delivered, and
a template is a fixed form with a few variables. It cannot carry a flat card
with a neighbourhood block and a list of nurseries.

In practice that leaves two ways to run it:

- **Twilio's WhatsApp sandbox.** Fine for one person. You join by sending a
  code to their number, messages carry a sandbox prefix, and **the join expires
  every 72 hours**, after which the bot goes quiet until you re-join. That
  silence looks exactly like a quiet market, which is the real hazard.
- **A real WhatsApp Business sender.** A business account, a dedicated number,
  template approval, and a per-message fee. Worth it for a company, rarely for
  one flat hunt.

Either way:

```sh
printf '%s' 'ACxxxxxxxx' > ~/.config/berlin-flat-bot/twilio_sid
printf '%s' 'your-auth-token' > ~/.config/berlin-flat-bot/twilio_token
chmod 600 ~/.config/berlin-flat-bot/twilio_*
```

WhatsApp has no HTML. The card is converted: bold becomes `*asterisks*`, tags
are stripped, and the message is capped at 1 500 characters, so a long card
loses its tail.

**Recommendation.** Use Telegram unless you have a reason not to. If you will
not install Telegram, use email. Choose WhatsApp only knowing about the 72-hour
re-join or the business account behind it.

## Checking it works

```sh
python3 -c "import sys; sys.path.insert(0,'src'); import notify, profile; \
            print(notify.check(profile.load()))"
```

That reports whether the channel is configured without sending anything.
