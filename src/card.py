#!/usr/bin/env python3
"""Turn a scored listing into the Telegram message.

The card has one job: let you decide without opening the listing. Every line
earns its place by answering a question you would otherwise have to click to
answer, and the order is the order you actually ask them in.

Why this order, since it was wrong twice before:

  1. **Where is it.** Ahead of the money. Rent means nothing until you know
     whether the address is somewhere you would live, and the map line used to
     sit fifth, below the price and the size, where you had to scroll to it.
  2. **How you get out.** Directly under the location, because transport is a
     gate rather than a range: if it is not there, the price and the size stop
     mattering.
  3. Money, age of the listing, size.
  4. The neighbourhood block.
  5. What is nearby, one line per thing you asked for.
  6. Good things, then bad things, then anything still unverified.

A rejected listing inverts all of it: the reason goes first and large, and the
score is not shown at all. 95/100 printed next to "does not qualify" tells you
nothing and reads as a near miss.
"""
import html, urllib.parse

import kiez


def _n(v, places=1):
    """Number without a trailing .0."""
    if v is None:
        return ""
    s = f"{float(v):.{places}f}".rstrip("0").rstrip(".")
    return s or "0"


def maps_url(address):
    q = " ".join((address or "").split()).strip(" ,.")
    if not q:
        return None
    if "berlin" not in q.lower():
        q += ", Berlin"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def _title(address):
    """Street with a number if there is one, otherwise district and postcode."""
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    return parts[0] if parts else "address not given"


def checks(listing, prof):
    """What still needs verifying, as a list. Empty is normal and good.

    Each entry is here because the bot could not settle it and the person has
    to. Nothing is listed that does not apply to them: somebody with no pet is
    never told to check the pet policy, because it is not their question and a
    line that is never relevant teaches you to skip the whole field.
    """
    import re
    out = []
    text = ((listing.get("title") or "") + " " + (listing.get("description") or "")).lower()
    if (prof.get("person") or {}).get("pets") and not re.search(
            r"haustier|hund|katze|tiere|pets?\b", text):
        out.append("pet policy")
    if not listing.get("warm"):
        out.append("Warmmiete")
    if not listing.get("rooms"):
        out.append("number of rooms")
    if not listing.get("size"):
        out.append("size")
    return out


def render(c, prof, markup=True):
    """c: score, addr, lat, lng, warm, warm_real, kalt, size, rooms, transit,
    anchors {label: minutes}, dist_km, flags, nearby (places.measure output),
    age, link, fails, check, source.
    """
    esc = html.escape if markup else (lambda s: s)
    b   = (lambda s: f"<b>{esc(s)}</b>") if markup else (lambda s: s)
    rep = prof.get("report") or {}
    out, body = [], []

    # ── head ────────────────────────────────────────────────────────────────
    if c.get("fails"):
        out.append(f"🔴 {b('DOES NOT QUALIFY')} · {esc(c['fails'][0])}\n{esc(_title(c.get('addr')))}")
    else:
        sc = c.get("score")
        dot = "🟢" if (sc or 0) >= 75 else "🟡"
        area = (c.get("kiez") or "").strip()
        lead = " · ".join(str(x) for x in (area, sc) if x not in (None, ""))
        out.append(f"{dot} {b(lead)} · {esc(_title(c.get('addr')))}")

    # ── 1. where ────────────────────────────────────────────────────────────
    bits = []
    parts = [p.strip() for p in (c.get("addr") or "").split(",") if p.strip()]
    where = " ".join(parts[1:]) if len(parts) > 1 else ""
    if where and where != c.get("kiez"):
        bits.append(where)
    if c.get("dist_km") is not None:
        bits.append(f"{_n(c['dist_km'])} km from the centre")
    if bits:
        line = " · ".join(bits)
        u = maps_url(c.get("addr"))
        body.append("📍 " + (f'<a href="{u}">{esc(line)}</a>' if (markup and u) else line))

    # ── 2. how you get out ──────────────────────────────────────────────────
    if c.get("transit"):
        body.append(c["transit"])
    if rep.get("commute", True) and c.get("anchors"):
        got = [f"{lbl} {m} min" for lbl, m in c["anchors"].items() if m is not None]
        if got:
            body.append("🧭 " + " · ".join(got))

    # ── 3. money ────────────────────────────────────────────────────────────
    warm, kalt, size = c.get("warm"), c.get("kalt"), c.get("size")
    money = []
    if warm:
        money.append(f"{warm:.0f} € warm" if c.get("warm_real")
                     else f"~{warm:.0f} € warm, estimated")
    if kalt:
        money.append(f"{kalt:.0f} € kalt")
    if kalt and size:
        money.append(f"{_n(kalt / size)} €/m²")
    if money:
        body.append("💰 " + " · ".join(money))
    extras = (prof.get("budget") or {}).get("extras_monthly")
    if warm and extras:
        body.append(f"   ≈ {warm + extras:.0f} € a month with power and internet")
    if c.get("age"):
        body.append("⏱ " + c["age"])

    dim = ([f"{_n(size)} m²"] if size else []) + \
          ([f"{c['rooms']:g} rooms"] if c.get("rooms") else [])
    if dim:
        body.append("📐 " + " · ".join(dim))

    # ── 4. the neighbourhood ────────────────────────────────────────────────
    if rep.get("kiez_stats", True) and c.get("lat") is not None:
        kb = kiez.block(c["lat"], c["lng"], markup=markup)
        if kb:
            body.append(kb)

    # ── 5. what is nearby ───────────────────────────────────────────────────
    if rep.get("nearby", True) and c.get("nearby"):
        import places
        for h in c["nearby"]:
            ln = places.line(h)
            if ln:
                body.append(ln)

    # ── 6. verdict ──────────────────────────────────────────────────────────
    good = [f for f in (c.get("flags") or []) if not _is_bad(f)]
    bad  = [f for f in (c.get("flags") or []) if _is_bad(f)]
    if good:
        body.append("✅ " + " · ".join(esc(g) for g in good[:5]))
    if bad:
        body.append("⚠️ " + " · ".join(esc(x) for x in bad[:4]))
    ck = c.get("check")
    if isinstance(ck, (list, tuple)):
        ck = ", ".join(ck)
    if ck:
        body.append("🔎 check: " + esc(ck))
    if len(c.get("fails") or []) > 1:
        body.append("⛔ also: " + esc("; ".join(c["fails"][1:])))

    out.append("\n".join(body))
    if c.get("source"):
        out.append(esc(c["source"]))
    if c.get("link"):
        out.append(c["link"])
    return "\n\n".join(x for x in out if x)


_BAD_WORDS = ("above", "tight", "expensive", "LOW PRIORITY", "space to heat",
              "more than needed", "suspiciously", "furnished", "mezzanine",
              "needs renovation")


def _is_bad(flag):
    return any(w.lower() in flag.lower() for w in _BAD_WORDS)
