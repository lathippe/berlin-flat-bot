#!/usr/bin/env python3
"""What kind of place this is, from Berlin's own neighbourhood statistics.

Berlin publishes figures for 543 planning areas (Planungsräume) under the LOR
scheme: who lives there by age, a composite social status with its trend, how
many people have stayed five years or more, recorded crime against the city
average, noise and greenery. `data/kiez-lor.json` holds them.

This is the part of the card that answers the question a listing photo never
does, which is what the street is like on a Tuesday evening. It says nothing
about the flat and everything about whether you would want to walk home to it.

Read the crime index carefully. `hz_x` is a multiplier against the Berlin
average, so 1.4 means forty per cent above average, not high in absolute terms,
and central districts with busy nightlife run high for reasons that have little
to do with living there. It is on the card because it is real, not because it
should decide anything on its own.

There is no encyclopedia blurb on the card. The source data carries one, and it
said things like "the northernmost and most densely built part of the borough",
which is true and useless: the six lines of statistics above it tell you more
about whether you want to live there than any general description can. It was
also the only thing in this module that needed translating.
"""
import html, json, pathlib

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "kiez-lor.json"

STATUS = {"hoch": "high", "mittel": "average", "niedrig": "low",
          "sehr niedrig": "very low"}
TREND  = {"positiv": "rising", "stabil": "stable", "negativ": "falling"}

_K = None


def _load():
    global _K
    if _K is None:
        _K = json.loads(DATA.read_text()) if DATA.exists() else {}
    return _K


def _in_poly(lat, lng, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        a1, b1 = ring[i]
        a2, b2 = ring[j]
        if (a1 > lat) != (a2 > lat) and lng < (b2 - b1) * (lat - a1) / (a2 - a1) + b1:
            inside = not inside
        j = i
    return inside


def lookup(lat, lng):
    """The raw record for this point, or None when it falls outside Berlin."""
    k = _load()
    if not k or lat is None or lng is None:
        return None
    lat, lng = float(lat), float(lng)
    area = next((q for q in k.get("kieze", []) if _in_poly(lat, lng, q["p"])), None)
    if not area:
        return None
    d = k["plr"].get(area["n"]) or k["plr"].get(f"{area['n']}|{area['bez']}")
    if not d:
        return None
    ortsteil = next((o["n"] for o in k.get("ortsteile", [])
                     if any(_in_poly(lat, lng, r) for r in o["p"])), None)
    return {"name": area["n"], "district": d.get("bez"), "ortsteil": ortsteil,
            **d}


def block(lat, lng, markup=True):
    """The neighbourhood lines for the card. Empty string when outside Berlin."""
    d = lookup(lat, lng)
    if not d:
        return ""
    b = (lambda s: f"<b>{html.escape(s)}</b>") if markup else (lambda s: s)
    pc = lambda v: f"{round(v)} %"

    part = d.get("ortsteil") or d.get("bzr")
    head = " · ".join(x for x in (
        part,
        d.get("district") if d.get("district") != part else None,
        f"{d['ew']:,}".replace(",", " ") + " residents" if d.get("ew") else None) if x)
    out = [f"🏘 {b(d['name'])} · {html.escape(head) if markup else head}"]

    ages = [(n, d.get(f)) for n, f in (("under 18", "pu18"), ("18–27", "p18_27"),
                                       ("27–45", "p27_45"), ("45–65", "p45_65"),
                                       ("65+", "p65")) if d.get(f) is not None]
    if ages:
        top = max(ages, key=lambda a: a[1])
        rest = " · ".join(f"{n} {round(v)}" for n, v in ages if n != top[0])
        out.append(f"👥 mostly {top[0]}, {pc(top[1])} · {rest}")

    st, dy = d.get("mss_st"), d.get("mss_dy")
    if st:
        good = st == "hoch" or (st == "mittel" and dy != "negativ")
        line = f"social status {STATUS.get(st, st)}"
        if dy:
            line += f", {TREND.get(dy, dy)}"
        out.append(("🟢 " if good else "🔴 ") + line)

    w = d.get("wohndauer5")
    if w is not None:
        mark = "🟢 " if w >= 60 else "🔴 " if w < 45 else ""
        out.append(f"{mark}{pc(w)} have lived here five years or more")

    hz = d.get("hz_x")
    if hz is not None:
        if hz < 0.9:
            out.append(f"🟢 crime below the city average, ×{hz:g}")
        elif hz > 1.1:
            out.append(("🔴 " if hz >= 1.8 else "") + f"crime above the city average, ×{hz:g}")
        else:
            out.append("crime around the city average")

    # Greenery carries no dot, in either direction. A red dot is for something
    # that could cost you, and a short supply of parks is a preference, not a
    # risk. Marking only the bad end would also be a lie by asymmetry: if the
    # absence gets a warning, the presence would have to get a reward.
    env = [{"gering": "🟢 quiet", "mittel": "some traffic noise",
            "hoch": "🔴 noisy"}.get(d.get("laerm")),
           {"gut": "plenty of green", "mittel": "some green space",
            "schlecht": "little green space"}.get(d.get("gruen"))]
    if any(env):
        out.append(" · ".join(e for e in env if e))

    return "\n".join(out)


if __name__ == "__main__":
    import sys
    la, ln = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (52.4886, 13.4253)
    print(block(la, ln, markup=False) or "outside Berlin")
