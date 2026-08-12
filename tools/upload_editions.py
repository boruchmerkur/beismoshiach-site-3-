# -*- coding: utf-8 -*-
"""Publish the Beis Moshiach print editions to archive.org, one item per issue.

Reads assets/editions.json (written by tools/scan_editions.py) and uploads the
matching PDF from C:\\Users\\BoruchMerkur\\Downloads\\beismoshiach-pdfs.

One item per issue rather than one big item, so every issue gets its own
citable URL and archive.org's own page-turner reader — which is what the site
embeds.

Just run it. If you have not signed in to archive.org on this machine it asks
once, at the prompt, and hands what you type straight to archive.org's own
client. Nothing is stored by this script.

    python3 tools/upload_editions.py             sign in if needed, then upload
    python3 tools/upload_editions.py --check     say what would go, send nothing
    python3 tools/upload_editions.py --limit=5   stop after five

Safe to stop and re-run: issues already on archive.org are skipped, so it
picks up where it left off. State is archive.org itself, not a local file.
"""
import os, io, sys, json, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:\Users\BoruchMerkur\Downloads\beismoshiach-pdfs"
DIR = {"he": "hebrew", "en": "english"}
MAN = os.path.join(ROOT, "assets", "editions.json")

CHECK = "--check" in sys.argv
LIMIT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)
ONLY = next((a.split("=")[1] for a in sys.argv if a.startswith("--lang=")), None)

TITLE = {"he": "בית משיח גליון %d", "en": "Beis Moshiach #%d"}
IALANG = {"he": "heb", "en": "eng"}


def ident(r):
    return "beis-moshiach-%s-%04d" % (r["lang"], r["n"])


def meta(r):
    m = {
        "title": TITLE[r["lang"]] % r["n"],
        "creator": "Beis Moshiach",
        "publisher": "Beis Moshiach",
        "mediatype": "texts",
        "collection": "opensource",
        "language": IALANG[r["lang"]],
        "subject": ["Chabad", "Lubavitch", "Moshiach", "Chassidus",
                    "Jewish periodicals", "Beis Moshiach"],
        "description": (
            "Issue %d of Beis Moshiach, the international Chabad-Lubavitch "
            "weekly. %d pages. Part of the complete run archived at "
            "<a href=\"https://beismoshiach.org/editions/\">beismoshiach.org</a>."
            % (r["n"], r["pages"])),
    }
    if r.get("date"):
        m["date"] = r["date"]
    return m


def signed_in():
    from internetarchive import get_session
    try:
        s = get_session()
        return bool(s.access_key and s.secret_key)
    except Exception:
        return False


def sign_in():
    """Hand straight over to archive.org's own client. What you type goes to
    them; this script never sees it and never writes it anywhere."""
    from internetarchive import configure
    print("\nOne-time sign-in to archive.org — your own account.")
    print("(If you have no account yet: https://archive.org/account/signup)\n")
    configure()
    print("\nSigned in.\n")


def human(sec):
    if sec < 90:
        return "%ds" % sec
    if sec < 5400:
        return "%dm" % (sec / 60)
    return "%dh %dm" % (sec // 3600, (sec % 3600) / 60)


def main():
    from internetarchive import get_item
    rows = json.load(io.open(MAN, encoding="utf-8"))["issues"]
    if ONLY:
        rows = [r for r in rows if r["lang"] == ONLY]
    rows.sort(key=lambda r: (r["lang"], r["n"]))

    missing = [r for r in rows
               if not os.path.isfile(os.path.join(SRC, DIR[r["lang"]], r["file"]))]
    if missing:
        print("!! %d files named in the manifest are not on disk, e.g. %s"
              % (len(missing), missing[0]["file"]))

    if CHECK:
        gb = sum(r["bytes"] for r in rows) / 1e9
        print("%d issues, %.2f GB, %d pages" % (len(rows), gb, sum(r["pages"] for r in rows)))
        for r in rows[:3] + rows[-2:]:
            print("  %-22s %-28s %s" % (ident(r), meta(r)["title"], r.get("date", "no date")))
        print("\nnothing sent — this was --check")
        return

    if not signed_in():
        sign_in()

    todo = sum(r["bytes"] for r in rows)
    print("%d issues, %.2f GB. Already-uploaded issues are skipped, so this can "
          "be stopped and re-run.\n" % (len(rows), todo / 1e9))

    sent = skipped = failed = 0
    done_bytes = 0
    t0 = time.time()
    for n, r in enumerate(rows, 1):
        i = ident(r)
        try:
            item = get_item(i)
            if item.exists:
                skipped += 1
                continue
        except Exception as e:
            print("  ?        %-22s could not check: %s" % (i, str(e)[:60]), flush=True)
            failed += 1
            continue
        p = os.path.join(SRC, DIR[r["lang"]], r["file"])
        if not os.path.isfile(p):
            failed += 1
            continue
        try:
            item.upload({"%s.pdf" % i: p}, metadata=meta(r),
                        retries=4, retries_sleep=12, verbose=False)
            sent += 1
            done_bytes += r["bytes"]
            rate = done_bytes / max(time.time() - t0, 1)
            left = sum(x["bytes"] for x in rows[n:])
            print("  %4d/%d  %-22s %6.1f MB   ~%s left"
                  % (n, len(rows), i, r["bytes"] / 1e6,
                     human(left / rate) if rate > 0 else "?"), flush=True)
        except Exception as e:
            failed += 1
            print("  FAILED   %-22s %s" % (i, str(e)[:90]), flush=True)
        if LIMIT and sent >= LIMIT:
            break
        time.sleep(1)                      # be a polite guest

    print("\nuploaded %d, already there %d, failed %d" % (sent, skipped, failed))
    if sent:
        print("Browse them: https://archive.org/search?query=creator%3A%22Beis+Moshiach%22")
    if failed:
        print("Re-run to retry the failures — everything already up is skipped.")


if __name__ == "__main__":
    main()
