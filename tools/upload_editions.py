# -*- coding: utf-8 -*-
"""Publish the Beis Moshiach print editions to archive.org, one item per issue.

Reads assets/editions.json (written by tools/scan_editions.py) and uploads the
matching PDF from C:\\Users\\BoruchMerkur\\Downloads\\beismoshiach-pdfs.

One item per issue rather than one big item, so every issue gets its own
citable URL and archive.org's own page-turner reader — which is what the site
embeds.

Credentials: run `ia configure` yourself first and enter your archive.org
login. This script never sees or stores a password; it only uses the config
that command writes.

    python3 tools/upload_editions.py --check          what would go, nothing sent
    python3 tools/upload_editions.py --go --limit=5   upload five, to eyeball
    python3 tools/upload_editions.py --go             the rest

Resumable: an issue already present on archive.org is skipped, so it can be
re-run after an interruption. State is archive.org itself, not a local file.
"""
import os, io, sys, json, time

# the Windows console is cp1252 and dies on the Hebrew titles
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:\Users\BoruchMerkur\Downloads\beismoshiach-pdfs"
DIR = {"he": "hebrew", "en": "english"}
MAN = os.path.join(ROOT, "assets", "editions.json")

GO = "--go" in sys.argv
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


def main():
    from internetarchive import get_item, configure  # noqa: F401
    rows = json.load(io.open(MAN, encoding="utf-8"))["issues"]
    if ONLY:
        rows = [r for r in rows if r["lang"] == ONLY]
    rows.sort(key=lambda r: (r["lang"], r["n"]))

    missing = [r for r in rows
               if not os.path.isfile(os.path.join(SRC, DIR[r["lang"]], r["file"]))]
    if missing:
        print("!! %d files named in the manifest are not on disk, e.g. %s"
              % (len(missing), missing[0]["file"]))

    if not GO:
        gb = sum(r["bytes"] for r in rows) / 1e9
        print("%d issues, %.2f GB, %d pages" % (len(rows), gb, sum(r["pages"] for r in rows)))
        for r in rows[:3] + rows[-2:]:
            print("  %-22s %-28s %s" % (ident(r), meta(r)["title"], r.get("date", "no date")))
        print("\nnothing sent — add --go to upload (run `ia configure` first)")
        return

    sent = skipped = failed = 0
    for r in rows:
        i = ident(r)
        item = get_item(i)
        if item.exists:
            skipped += 1
            continue
        p = os.path.join(SRC, DIR[r["lang"]], r["file"])
        if not os.path.isfile(p):
            failed += 1
            continue
        try:
            item.upload({"%s.pdf" % i: p}, metadata=meta(r),
                        retries=4, retries_sleep=12, verbose=False)
            sent += 1
            print("  uploaded %-22s %6.1f MB" % (i, r["bytes"] / 1e6), flush=True)
        except Exception as e:
            failed += 1
            print("  FAILED   %-22s %s" % (i, str(e)[:90]), flush=True)
        if LIMIT and sent >= LIMIT:
            break
        time.sleep(1)                      # be a polite guest
    print("\nuploaded %d, already there %d, failed %d" % (sent, skipped, failed))


if __name__ == "__main__":
    main()
