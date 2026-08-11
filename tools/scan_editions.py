# -*- coding: utf-8 -*-
"""Inventory the Beis Moshiach print editions and pull a cover from each.

Reads C:\\Users\\BoruchMerkur\\Downloads\\beismoshiach-pdfs (hebrew/ and english/)
and writes, into the site:

    assets/editions.json          one row per issue: number, language, pages,
                                  bytes, cover file, and whether it opens
    storage/editions/<lang>-<n>.jpg   page 1 at 320px wide

Every issue is opened and page 1 is actually rendered, because a PDF can carry
a page tree and still be empty — 46 of the files on the old magazine site were
truncated at exactly 1 MiB and MuPDF happily "repairs" them into 130 blank
pages. A file that renders a blank first page is reported, not published.

The PDFs themselves are never modified, and no text is extracted for display:
these use pre-Unicode Hebrew fonts whose text layer comes out as keyboard
mash, and guessing at it is exactly how Torah text gets corrupted.

Resumable — rows already in editions.json are kept unless --force.

    python3 tools/scan_editions.py [--force] [--limit N]
"""
import os, io, re, sys, json, warnings

warnings.filterwarnings("ignore")
import fitz                                    # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:\Users\BoruchMerkur\Downloads\beismoshiach-pdfs"
COVERS = os.path.join(ROOT, "storage", "editions")
OUT = os.path.join(ROOT, "assets", "editions.json")
LANGS = {"hebrew": "he", "english": "en"}
COVER_W = 320

FORCE = "--force" in sys.argv
LIMIT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)


def issue_no(name):
    """383.pdf, 1165_BRM.pdf, 'Beis Moshiach #1210.pdf' — the number is the
    only thing these agree on."""
    m = re.search(r"(\d{1,4})", name)
    return int(m.group(1)) if m else None


def blank(page):
    """A rendered page with one or two distinct colours is empty paper."""
    px = page.get_pixmap(dpi=36)
    step = 3 * 97                              # sparse sample, not every pixel
    seen = {px.samples[i:i + 3] for i in range(0, len(px.samples) - 3, step)}
    return len(seen) <= 2


def cover(doc, path):
    page = doc[0]
    z = COVER_W / page.rect.width
    px = page.get_pixmap(matrix=fitz.Matrix(z, z))
    px.save(path, jpg_quality=78)


def scan(lang_dir, code, rows, seen):
    d = os.path.join(SRC, lang_dir)
    if not os.path.isdir(d):
        print("  (no %s folder)" % lang_dir)
        return
    files = sorted(os.listdir(d), key=lambda f: (issue_no(f) or 0, f))
    done = 0
    for f in files:
        if not f.lower().endswith(".pdf"):
            continue
        n = issue_no(f)
        key = "%s-%s" % (code, n)
        if key in seen and not FORCE:
            continue
        p = os.path.join(d, f)
        row = {"k": key, "n": n, "lang": code, "file": f,
               "bytes": os.path.getsize(p)}
        cov = os.path.join(COVERS, key + ".jpg")
        try:
            doc = fitz.open(p)
            row["pages"] = doc.page_count
            row["repaired"] = bool(getattr(doc, "is_repaired", False))
            if doc.page_count == 0:
                row["ok"] = False
                row["why"] = "no pages"
            else:
                row["ok"] = not blank(doc[0])
                if not row["ok"]:
                    row["why"] = "first page renders blank"
                else:
                    cover(doc, cov)
                    row["cover"] = "storage/editions/%s.jpg" % key
            doc.close()
        except Exception as e:
            row["ok"] = False
            row["pages"] = 0
            row["why"] = str(e)[:90]
        rows.append(row)
        seen.add(key)
        done += 1
        if done % 25 == 0:
            save(rows)
            print("    %s %d/%d" % (code, done, len(files)), flush=True)
        if LIMIT and done >= LIMIT:
            break


def save(rows):
    rows.sort(key=lambda r: (r["lang"], r["n"] or 0))
    tmp = OUT + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"issues": rows}, fh, ensure_ascii=False, indent=0)
    os.replace(tmp, OUT)


def main():
    os.makedirs(COVERS, exist_ok=True)
    rows, seen = [], set()
    if os.path.isfile(OUT) and not FORCE:
        rows = json.load(io.open(OUT, encoding="utf-8"))["issues"]
        seen = {r["k"] for r in rows}
        print("resuming with %d already scanned" % len(rows))
    for d, code in LANGS.items():
        print("scanning %s…" % d, flush=True)
        scan(d, code, rows, seen)
    save(rows)
    ok = [r for r in rows if r.get("ok")]
    bad = [r for r in rows if not r.get("ok")]
    print("\n%d issues: %d usable, %d not" % (len(rows), len(ok), len(bad)))
    for code in ("he", "en"):
        g = [r for r in ok if r["lang"] == code]
        if g:
            print("  %s: %d issues, %d pages, %.1f GB"
                  % (code, len(g), sum(r["pages"] for r in g),
                     sum(r["bytes"] for r in g) / 1e9))
    for r in bad[:12]:
        print("  unusable: %-9s %s" % (r["k"], r.get("why", "")))
    if len(bad) > 12:
        print("  … and %d more" % (len(bad) - 12))


if __name__ == "__main__":
    main()
