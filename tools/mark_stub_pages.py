#!/usr/bin/env python3
"""
The weekly "click for articles on the parsha" posts are navigation, not articles.

A deep crawl (1,500 pages, 2026-09-15) found 56 pages on the site that carry no
readable text. They are NOT lost content — every one of them is intact in this
repo, and the bodies are exactly what the magazine published:

  * 44 are weekly index posts whose entire body is "Click for articles on the
    Parsha · Click for more articles & videos" and a couple of links. They were
    never written; their job was to point at the week's real articles.
  * 7 are video posts — a Facebook or YouTube embed and nothing else.
  * 3 are genuinely short articles with real prose.
  * 1 is search.html, which carries a 19 MB index inline and shows 462 characters.

This marks the navigation posts and the search page `noindex,follow` and takes
them out of the sitemap. `follow` matters: these pages exist to pass a reader on
to the week's articles, and they go on doing exactly that. Nothing is deleted,
no body is touched, and every one of them still answers 200 to anyone who has
the link.

The video posts and the three short articles are LEFT ALONE. A video post is
thin because it is a video, not because anything is missing.

    python tools/mark_stub_pages.py            # report
    python tools/mark_stub_pages.py --write
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"
TAG = '<meta name="robots" content="noindex,follow">'
BODY = re.compile(r'(?is)<div class="entry-body">(.*?)</div>\s*\n\s*<div class="citebox"')
# The phrase the weekly index posts are built out of, in every spelling it took.
NAV = re.compile(r"click\s+for\s+(articles|videos|more)", re.I)
EXTRA = ["search.html"]


def body_of(html):
    m = BODY.search(html)
    return m.group(1) if m else ""


def is_nav_stub(html):
    """Body is link text and nothing else."""
    b = body_of(html)
    if re.search(r"<iframe|<img", b, re.I):
        return False
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b)).strip()
    if len(txt) > 220:
        return False
    return bool(NAV.search(txt))


def main(write):
    hits, skipped = [], []
    for f in sorted((ROOT / "articles").glob("*.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        if not is_nav_stub(html):
            continue
        if re.search(r'name=["\']robots', html, re.I):
            skipped.append(f.name)
            continue
        hits.append(f)
    for name in EXTRA:
        f = ROOT / name
        if f.exists() and not re.search(r'name=["\']robots',
                                        f.read_text(encoding="utf-8", errors="replace")[:4000], re.I):
            hits.append(f)

    print(f"{len(hits)} pages to mark noindex,follow"
          + (f" ({len(skipped)} already marked)" if skipped else ""))
    for f in hits[:6]:
        print("   ", f.relative_to(ROOT).as_posix())
    if len(hits) > 6:
        print(f"    … and {len(hits) - 6} more")

    sm = SITEMAP.read_text(encoding="utf-8")
    before = sm.count("<loc>")
    for f in hits:
        rel = f.relative_to(ROOT).as_posix()
        sm = re.sub(r"\s*<url>\s*<loc>[^<]*/" + re.escape(rel) + r"</loc>.*?</url>",
                    "", sm, flags=re.S)
    print(f"\nsitemap {before} -> {sm.count('<loc>')} URLs")

    if not write:
        print("report only - re-run with --write to apply")
        return
    for f in hits:
        html = f.read_text(encoding="utf-8", errors="replace")
        out = re.sub(r"</title>", "</title>\n" + TAG, html, count=1, flags=re.I)
        if out == html:
            print("  !! no </title> in", f.name)
            continue
        f.write_text(out, encoding="utf-8")
    SITEMAP.write_text(sm, encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main("--write" in sys.argv)
