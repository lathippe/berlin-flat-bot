#!/usr/bin/env python3
"""Read what Fredy has found and send you the ones worth your evening.

    python3 src/watch.py --dry          decide and print, send nothing
    python3 src/watch.py                for real
    python3 src/watch.py --all          ignore the seen list and redo everything

Fredy scrapes the portals and writes to its own SQLite database. This reads
that database rather than taking a webhook: a poll has no server to keep up, no
port to open, and if this is not running when Fredy finds something, nothing is
lost. It just arrives at the next run.

Put it on a timer every ten or fifteen minutes. More often does not help, since
the portals do not publish faster than that, and the routing calls are not free.

Every run ends with a tally of why listings were dropped. Read it. A gate that
is quietly too tight looks exactly like a quiet market, and the tally is the
only thing that tells them apart.
"""
import argparse, collections, os, pathlib, sqlite3, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import card, notify, pipeline, profile as P, state, transit, kiez

DEFAULT_DB = pathlib.Path(os.path.expanduser("~/fredy/db/listings.db"))


def rows_from_fredy(db, include_inactive=False):
    """Fredy's listings, without disturbing Fredy.

    Opened read-only first. That fails more often than you would expect:
    Fredy keeps the database in WAL mode, and a read-only connection cannot
    replay a write-ahead log, so it refuses to open at all rather than
    returning stale rows. When that happens the database and its log are
    copied to a temporary file and read there, which is slower by a fraction
    of a second and cannot interfere with a running scraper under any
    circumstances.
    """
    db = pathlib.Path(db)
    if not db.exists():
        sys.exit(f"No Fredy database at {db}.\n"
                 f"Start Fredy and create at least one job first: docs/fredy.md.\n"
                 f"Point somewhere else with --db.")
    where = "" if include_inactive else "where is_active=1 and coalesce(manually_deleted,0)=0"
    sql = f"select * from listings {where}"

    def read(path, uri=False):
        con = sqlite3.connect(path, uri=uri)
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(sql)]
        finally:
            con.close()

    try:
        return read(f"file:{db}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        pass
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / db.name
        for suffix in ("", "-wal", "-shm"):
            src = db.with_name(db.name + suffix)
            if src.exists():
                shutil.copy2(src, copy.with_name(copy.name + suffix))
        return read(str(copy))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--dry", action="store_true", help="decide and print, send nothing")
    ap.add_argument("--all", action="store_true", help="ignore the seen list")
    ap.add_argument("--limit", type=int, help="stop after this many sends")
    ap.add_argument("--profile")
    a = ap.parse_args()

    prof = P.load(a.profile)
    st = state.load()
    ok, why = notify.check(prof)
    if not a.dry and not ok:
        sys.exit(f"Delivery is not set up: {why}\nSee docs/delivery.md, or use --dry.")

    rows = rows_from_fredy(a.db)
    fresh = [r for r in rows if a.all or not state.seen(st, r)]
    print(f"{len(rows)} listings in Fredy, {len(fresh)} not looked at yet\n")

    sent, why_not, shortlist = 0, collections.Counter(), []
    for row in sorted(fresh, key=lambda r: -(r.get("created_at") or 0)):
        reason, info = pipeline.process(row, prof, st)
        state.remember_seen(st, row)

        if reason:
            why_not[info.get("kind") or reason] += 1
            if a.dry:
                print(f"  ✖ {reason:34} {(row.get('address') or '?')[:46]}")
            continue

        k = kiez.lookup(row["latitude"], row["longitude"])
        text = card.render(dict(
            score=info["score"], addr=row.get("address"),
            lat=row["latitude"], lng=row["longitude"], kiez=(k or {}).get("name"),
            warm=info["warm"], warm_real=info["warm_real"], kalt=row.get("price"),
            size=row.get("size"), rooms=row.get("rooms"),
            transit=info["transit"], anchors={x["label"]: info["anchors"].get(x["id"])
                                              for x in prof.get("anchors", [])},
            dist_km=info["dist_km"], flags=info["flags"], nearby=info.get("nearby"),
            check=card.checks(info["listing"], prof),
            source=f"via {row.get('provider')}" if row.get("provider") else None,
            link=row.get("link"),
        ), prof, markup=not a.dry)

        if a.dry:
            print(f"\n  ✔ {info['score']} · {(row.get('address') or '?')[:60]}")
        else:
            notify.send(text, prof, link=row.get("link"),
                        lat=row["latitude"], lng=row["longitude"])
            state.remember_sent(st, row, info["score"])
        sent += 1
        shortlist.append((info["score"], row.get("address") or "?", row.get("link")))
        if a.limit and sent >= a.limit:
            break

    transit.save()
    if not a.dry:
        state.save(st)

    print(f"\nsent: {sent}")
    for sc, addr, _ in sorted(shortlist, reverse=True):
        print(f"  ✔ {sc:3d} · {addr[:64]}")
    if why_not:
        print("\nnot sent:")
        for reason, n in why_not.most_common():
            print(f"  {n:4d}  {reason}")
        print("\n\033[2mA reason near the top of that list with a large number is "
              "usually a gate set tighter than you meant.\033[0m")


if __name__ == "__main__":
    main()
