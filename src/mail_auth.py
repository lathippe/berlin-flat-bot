#!/usr/bin/env python3
"""One-time Gmail consent. Run once, then the mail watcher works on its own.

    python3 src/mail_auth.py

Needs an OAuth client of your own at ~/.config/berlin-flat-bot/oauth.json.
docs/mail.md walks through creating one; it is five clicks in Google Cloud
Console and the client is yours, not shared.

This opens a browser, waits for you to approve, and writes a refresh token next
to the client file. Nothing leaves your machine except the exchange with
Google. Stdlib only, no googleapiclient.
"""
import http.server, json, pathlib, secrets, socket, sys, threading
import urllib.parse, urllib.request, webbrowser

CONF   = pathlib.Path.home() / ".config" / "berlin-flat-bot"
CLIENT = CONF / "oauth.json"
TOKENS = CONF / "tokens.json"

AUTH  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
# modify, not readonly: the watcher labels and archives what it has processed.
# Run it with --no-label --no-archive and gmail.readonly is enough; change the
# scope here if you would rather it could never touch anything.
SCOPE = "https://www.googleapis.com/auth/gmail.modify"


def load_client():
    if not CLIENT.exists():
        sys.exit(f"No OAuth client at {CLIENT}\n"
                 f"Create one and save it there. See docs/mail.md.")
    raw = json.loads(CLIENT.read_text())
    c = raw.get("installed") or raw.get("web") or raw
    if not c.get("client_id"):
        sys.exit(f"{CLIENT} has no client_id. Download the Desktop app client "
                 f"JSON from Google Cloud Console, not the API key.")
    if raw.get("web"):
        print("  note: that is a Web client. A Desktop app client is the right "
              "kind here, but this will work if the redirect URI is registered.")
    return c["client_id"], c.get("client_secret", "")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Catcher(http.server.BaseHTTPRequestHandler):
    """Receives the redirect Google sends the browser to."""
    result = {}

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        Catcher.result = {k: v[0] for k, v in q.items()}
        ok = "code" in Catcher.result
        body = ("<h2>Done.</h2><p>You can close this tab and go back to the terminal.</p>"
                if ok else
                f"<h2>Something went wrong.</h2><pre>{Catcher.result}</pre>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body style='font:16px system-ui;padding:3em'>{body}</body></html>".encode())
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *a):
        pass                              # the default logger writes to stderr


def post(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    try:
        return json.load(urllib.request.urlopen(url, data, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit(f"Google refused the exchange:\n{e.read().decode('utf8', 'replace')[:400]}")


def main():
    cid, secret = load_client()
    port  = free_port()
    redir = f"http://127.0.0.1:{port}/"
    state = secrets.token_urlsafe(16)

    url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redir, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent",
        "state": state,
    })

    srv = http.server.HTTPServer(("127.0.0.1", port), Catcher)
    print("Opening your browser to approve access.")
    print(f"If nothing happens, open this yourself:\n\n  {url}\n")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit("\ncancelled")

    r = Catcher.result
    if r.get("state") != state:
        sys.exit("State mismatch. Start again; do not reuse that browser tab.")
    if "code" not in r:
        sys.exit(f"No code came back: {r.get('error_description') or r}")

    tok = post(TOKEN, {"code": r["code"], "client_id": cid, "client_secret": secret,
                       "redirect_uri": redir, "grant_type": "authorization_code"})
    if "refresh_token" not in tok:
        sys.exit("Google returned no refresh token. That usually means this "
                 "client was already authorised. Revoke it at "
                 "myaccount.google.com/permissions and run this again.")

    CONF.mkdir(parents=True, exist_ok=True)
    TOKENS.write_text(json.dumps({"refresh_token": tok["refresh_token"],
                                  "client_id": cid, "client_secret": secret,
                                  "scope": SCOPE}, indent=2))
    TOKENS.chmod(0o600)
    print(f"Refresh token written to {TOKENS}")
    print("\nWhile the consent screen stays in testing mode this token expires "
          "after seven days.\nIf the watcher starts failing to authenticate "
          "about a week from now, run this again\nor publish the consent screen.")


if __name__ == "__main__":
    main()
