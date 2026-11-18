#!/usr/bin/env python3
"""Deliver a card, by whichever route this person actually reads.

    send(text, prof, link=None, lat=None, lng=None)

Three channels. They are not equally good for this job, and the differences
are not cosmetic, so pick with them in mind.

**Telegram** is the best fit and the least work. A bot token takes two minutes,
costs nothing, carries HTML, and renders a map. If there is no reason to
prefer something else, prefer this.

**Email** is the most portable. Nothing to install, works on any phone, and a
flat hunt is already happening in your inbox, so the alerts sit next to the
replies. Slower to notice, which matters in a market where a good flat is gone
in a day. Two ways in: a plain SMTP account, or the Gmail credentials already
set up for the mail watcher, which avoids a second secret.

**WhatsApp** is the one people ask for and the one that fights back. Meta does
not let a business send a free-form message to someone who has not written
first: outside a 24-hour window opened by *their* message, only pre-approved
templates go through, and a template cannot carry a flat card. In practice that
means either replying to yourself every day to hold the window open, or using
the Twilio sandbox, which is fine for one person but shows a sandbox prefix and
needs re-joining every 72 hours. It also costs money per message. It works, and
it is supported here, but go in knowing that.
"""
import json, os, pathlib, smtplib, urllib.error, urllib.parse, urllib.request
from email.message import EmailMessage

CONF = pathlib.Path(os.path.expanduser("~/.config/berlin-flat-bot"))


def _secret(name, env=None):
    """A secret from the environment, else from ~/.config/berlin-flat-bot/<name>."""
    if env and os.environ.get(env):
        return os.environ[env].strip()
    f = CONF / name
    if f.exists():
        return f.read_text().strip()
    return None


def _post(url, data, headers=None, timeout=25):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, body, headers or {})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


# ───────────────────────────────── telegram ─────────────────────────────────

def _telegram(text, prof, link=None, lat=None, lng=None):
    token = _secret("telegram_token", "FLATBOT_TELEGRAM_TOKEN")
    chat  = (prof.get("delivery") or {}).get("telegram_chat_id") \
            or (prof.get("person") or {}).get("telegram_chat_id")
    if not token or not chat:
        raise RuntimeError("Telegram needs a token in ~/.config/berlin-flat-bot/"
                           "telegram_token and a chat id in the profile. See docs/delivery.md.")
    r = _post(f"https://api.telegram.org/bot{token}/sendMessage",
              {"chat_id": chat, "text": text, "parse_mode": "HTML",
               "disable_web_page_preview": "false" if link else "true"})
    return bool(r.get("ok"))


# ────────────────────────────────── email ───────────────────────────────────

def _email(text, prof, link=None, lat=None, lng=None):
    d = prof.get("delivery") or {}
    to = d.get("email")
    if not to:
        raise RuntimeError("delivery.email is not set in the profile.")
    subject = text.split("\n", 1)[0][:120]

    msg = EmailMessage()
    msg["To"], msg["Subject"] = to, subject
    # The card is already HTML for Telegram, and both renderings are useful:
    # the plain part is what a watch or a notification preview shows.
    import re
    plain = re.sub(r"<[^>]+>", "", text)
    msg.set_content(plain)
    msg.add_alternative("<pre style='font:14px/1.5 -apple-system,system-ui,sans-serif;"
                        "white-space:pre-wrap'>" + text + "</pre>", subtype="html")

    if d.get("smtp_host"):
        msg["From"] = d.get("smtp_from") or to
        pw = _secret("smtp_password", "FLATBOT_SMTP_PASSWORD")
        with smtplib.SMTP(d["smtp_host"], int(d.get("smtp_port") or 587), timeout=30) as s:
            s.starttls()
            if d.get("smtp_user") and pw:
                s.login(d["smtp_user"], pw)
            s.send_message(msg)
        return True

    # Otherwise reuse the Gmail OAuth the mail watcher already needs, so there
    # is one set of credentials rather than two.
    import base64
    tok = CONF / "tokens.json"
    if not tok.exists():
        raise RuntimeError("No SMTP settings and no Gmail token. Either set "
                           "delivery.smtp_host in the profile, or run "
                           "`python3 src/mail_auth.py`. See docs/delivery.md.")
    t = json.loads(tok.read_text())
    access = _post("https://oauth2.googleapis.com/token",
                   {"client_id": t["client_id"], "client_secret": t.get("client_secret", ""),
                    "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}
                   )["access_token"]
    msg["From"] = to
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json.dumps({"raw": raw}).encode(),
        {"Authorization": "Bearer " + access, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)
    return True


# ───────────────────────────────── whatsapp ─────────────────────────────────

def _whatsapp(text, prof, link=None, lat=None, lng=None):
    """Via Twilio. See the module docstring for why this is the awkward one."""
    d = prof.get("delivery") or {}
    sid   = _secret("twilio_sid", "TWILIO_ACCOUNT_SID")
    tok   = _secret("twilio_token", "TWILIO_AUTH_TOKEN")
    to    = d.get("whatsapp")
    frm   = d.get("whatsapp_from") or "whatsapp:+14155238886"   # Twilio sandbox
    if not (sid and tok and to):
        raise RuntimeError("WhatsApp needs a Twilio SID and token in "
                           "~/.config/berlin-flat-bot/ and delivery.whatsapp in the "
                           "profile. See docs/delivery.md.")
    import base64, re
    # WhatsApp has no HTML. Bold is *asterisks*, and tags must go or they show
    # up literally.
    body = re.sub(r"</?b>", "*", text)
    body = re.sub(r"<[^>]+>", "", body)
    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    _post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
          {"From": frm, "To": to if to.startswith("whatsapp:") else "whatsapp:" + to,
           "Body": body[:1500]},
          {"Authorization": "Basic " + auth})
    return True


CHANNELS = {"telegram": _telegram, "email": _email, "whatsapp": _whatsapp}

# What each channel can render. The card asks for this so it does not send
# HTML tags to a channel that shows them literally.
FORMAT = {"telegram": "html", "email": "html", "whatsapp": "whatsapp"}


def channel(prof):
    return (prof.get("delivery") or {}).get("channel") or "telegram"


# The first failure anybody hits, and what it actually means. A raw traceback
# with an HTTP code tells a person nothing about what to go and fix.
_HINTS = {
    ("telegram", 401): "The bot token is wrong. Check "
                       "~/.config/berlin-flat-bot/telegram_token against what "
                       "@BotFather gave you.",
    ("telegram", 400): "Telegram refused the message. Usually the chat id is "
                       "wrong, or you have not sent your bot a message yet: a "
                       "bot may not write to you until you have written to it.",
    ("telegram", 403): "Your bot is blocked, or you have never messaged it. "
                       "Open the chat and send it anything, then try again.",
    ("whatsapp", 401): "Twilio rejected the credentials. Check twilio_sid and "
                       "twilio_token in ~/.config/berlin-flat-bot/.",
    ("whatsapp", 400): "Twilio refused the message. With the sandbox this is "
                       "almost always the 72-hour join having expired: send "
                       "the join code to the sandbox number again. See "
                       "docs/delivery.md.",
}


def send(text, prof, link=None, lat=None, lng=None):
    ch = channel(prof)
    fn = CHANNELS.get(ch)
    if not fn:
        raise RuntimeError(f"Unknown delivery channel {ch!r}. "
                           f"One of: {', '.join(CHANNELS)}")
    try:
        return fn(text, prof, link=link, lat=lat, lng=lng)
    except urllib.error.HTTPError as exc:
        hint = _HINTS.get((ch, exc.code))
        detail = ""
        try:
            detail = exc.read().decode("utf8", "replace")[:200]
        except Exception:
            pass
        raise RuntimeError(
            f"{ch} refused the message (HTTP {exc.code})."
            + (f"\n  {hint}" if hint else "")
            + (f"\n  {detail}" if detail else "")) from None
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPException) as exc:
        raise RuntimeError(
            f"The mail server refused it: {type(exc).__name__}.\n"
            f"  For Gmail over SMTP the password has to be an App Password, "
            f"not your account password, and App Passwords need two-factor "
            f"authentication switched on. See docs/delivery.md.") from None
    except OSError as exc:
        raise RuntimeError(f"Could not reach {ch}: {exc}.\n"
                           f"  Network, or the host and port are wrong.") from None


def check(prof):
    """Say whether delivery is actually configured, without sending anything."""
    ch = channel(prof)
    try:
        if ch == "telegram":
            if not _secret("telegram_token", "FLATBOT_TELEGRAM_TOKEN"):
                return False, "no telegram_token in ~/.config/berlin-flat-bot/"
            if not ((prof.get("delivery") or {}).get("telegram_chat_id")
                    or (prof.get("person") or {}).get("telegram_chat_id")):
                return False, "no telegram chat id in the profile"
        elif ch == "email":
            if not (prof.get("delivery") or {}).get("email"):
                return False, "delivery.email is not set"
            if not (prof.get("delivery") or {}).get("smtp_host") \
                    and not (CONF / "tokens.json").exists():
                return False, "neither SMTP settings nor a Gmail token"
        elif ch == "whatsapp":
            if not _secret("twilio_sid", "TWILIO_ACCOUNT_SID"):
                return False, "no twilio_sid in ~/.config/berlin-flat-bot/"
            if not (prof.get("delivery") or {}).get("whatsapp"):
                return False, "delivery.whatsapp is not set"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, f"{ch} looks configured"
