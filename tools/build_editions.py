# -*- coding: utf-8 -*-
"""Build editions/index.html — the full run of the printed magazine.

Reads assets/editions.json and writes a browsable shelf: every issue as its
cover, filterable by language and searchable by number or date. Each cover
links to that issue's archive.org item, which holds the PDF and archive.org's
own page-turner reader.

    python3 tools/build_editions.py
"""
import os, io, re, json, html, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "assets", "editions.json")
OUT = os.path.join(ROOT, "editions", "index.html")
IA = "https://archive.org/details/beis-moshiach-%s-%04d"

esc = lambda s: html.escape(str(s), quote=True)

MONTH = ["", "January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"]


def pretty(d):
    if not d:
        return ""
    y, m, dd = (int(x) for x in d.split("-"))
    return "%d %s %d" % (dd, MONTH[m][:3], y)


def card(r):
    href = IA % (r["lang"], r["n"])
    date = pretty(r.get("date"))
    sub = " · ".join(x for x in [date, "%d pp" % r["pages"]] if x)
    return (
        '<a class="ed" href="{h}" target="_blank" rel="noopener" '
        'data-n="{n}" data-lang="{l}" data-d="{d}">'
        '<figure><img src="/{c}" alt="" loading="lazy" width="320"></figure>'
        '<span class="no">#{n}</span><span class="sub">{s}</span></a>'
    ).format(h=esc(href), n=r["n"], l=r["lang"], d=esc(r.get("date", "")),
             c=esc(r.get("cover", "")), s=esc(sub))


def main():
    rows = json.load(io.open(MAN, encoding="utf-8"))["issues"]
    rows = [r for r in rows if r.get("ok") and r.get("cover")]
    rows.sort(key=lambda r: (r["lang"] != "en", r["n"]))
    by = collections.Counter(r["lang"] for r in rows)
    pages = sum(r["pages"] for r in rows)

    groups = []
    for lang, label, native in (("en", "English", "English"),
                                ("he", "Hebrew", "לשון הקודש")):
        rs = [r for r in rows if r["lang"] == lang]
        if not rs:
            continue
        groups.append(
            '<section class="lang" id="%s"><h2>%s <span class="cnt">%d issues · %s–%s</span></h2>'
            '<div class="grid">%s</div></section>'
            % (lang, esc(native), len(rs), rs[0]["n"], rs[-1]["n"],
               "".join(card(r) for r in rs)))

    doc = TEMPLATE.format(
        total=len(rows), pages="{:,}".format(pages),
        en=by["en"], he=by["he"], groups="".join(groups))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
    print("editions/index.html: %d issues (%d en, %d he), %s pages"
          % (len(rows), by["en"], by["he"], "{:,}".format(pages)))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The printed magazine — beismoshiach.org</title>
<meta name="description" content="Every issue of Beis Moshiach in print — {total} editions, {pages} pages, English and Hebrew, free to read.">
<!-- Held back from search until the archive.org items exist: indexing 814
     links that 404 would earn the site nothing but broken-link reports.
     Remove this line once tools/upload_editions.py has finished. -->
<meta name="robots" content="noindex,follow">
<link rel="stylesheet" href="/assets/site.css">
<style>
  .ed-head{{max-width:1400px;margin:0 auto;padding:2.6rem clamp(1.25rem,4vw,4rem) 1rem}}
  .ed-head h1{{font-family:var(--display);font-size:clamp(2rem,5vw,3.4rem);line-height:1.03;
    letter-spacing:-.02em;margin:0 0 .5rem}}
  .ed-head p{{max-width:60ch;color:var(--ink-soft);line-height:1.6;margin:0 0 1.2rem}}
  .tools{{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center}}
  .tools input{{font:inherit;font-size:.95rem;padding:.5rem .8rem;border:1px solid var(--rule);
    border-radius:999px;background:var(--surface);color:var(--ink);min-width:15ch}}
  .tools a{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
    text-decoration:none;color:var(--ink-soft);border:1px solid var(--rule);
    border-radius:999px;padding:.45rem .9rem}}
  .tools a:hover{{color:var(--royal);border-color:var(--royal)}}
  .lang{{max-width:1400px;margin:0 auto;padding:1.4rem clamp(1.25rem,4vw,4rem) 2rem}}
  .lang h2{{font-family:var(--display);font-size:1.5rem;margin:0 0 1rem;
    display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap}}
  .cnt{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
    color:var(--ink-soft);font-weight:400}}
  .grid{{display:grid;gap:1.4rem 1rem;
    grid-template-columns:repeat(auto-fill,minmax(126px,1fr))}}
  .ed{{text-decoration:none;color:inherit;display:flex;flex-direction:column;gap:.35rem}}
  .ed figure{{margin:0;overflow:hidden;background:var(--parchment-deep);
    border:1px solid var(--rule);box-shadow:0 2px 10px rgba(10,10,11,.07)}}
  .ed img{{display:block;width:100%;height:auto;transition:transform .5s var(--ease)}}
  .ed:hover img{{transform:scale(1.04)}}
  .ed:hover .no{{color:var(--royal)}}
  .no{{font-family:var(--mono);font-size:12px;font-weight:500}}
  .sub{{font-family:var(--mono);font-size:10px;letter-spacing:.04em;color:var(--ink-soft)}}
  .ed[hidden]{{display:none}}
  .empty{{color:var(--ink-soft);font-style:italic;padding:1rem 0}}
  @media(max-width:560px){{.grid{{grid-template-columns:repeat(auto-fill,minmax(98px,1fr))}}}}
</style>
</head>
<body>
<header class="bm-topbar"><div class="bm-inner">
  <a class="bm-wordmark" href="/">beismoshiach<span class="bm-tld">.org</span></a>
  <nav><a href="/topics">Topics</a><a href="/parsha">Parsha</a><a href="/collections">Collections</a>
    <a href="/archives">Archives</a><a href="/search">Search</a><a class="langsw" href="/he/">עברית</a></nav>
</div></header>

<main>
<div class="ed-head">
  <h1>The magazine, in print</h1>
  <p>Every issue we hold, scanned whole — {total} editions across {pages} pages,
     {en} in English and {he} in לשון הקודש. Each one opens in a page-turner and
     downloads as a PDF. Nothing here is retyped or corrected; the issues are
     exactly as they were printed.</p>
  <div class="tools">
    <input id="q" type="search" placeholder="Issue number or year" aria-label="Filter issues">
    <a href="#en">English</a><a href="#he">לשון הקודש</a><a href="/archives">Article archive</a>
  </div>
</div>
{groups}
</main>

<footer class="colophon"><div class="wrap">
  <div class="cf-brand">beismoshiach.org</div>
  The printed run, preserved. Hosted with the Internet Archive.
</div></footer>

<script>
/* Filter on issue number or year. The year comes from the date we could verify;
   an issue with no verified date stays visible on a numeric search only, since
   claiming a year we do not know would be worse than showing nothing. */
(function(){{
  var q=document.getElementById('q'); if(!q) return;
  var eds=[].slice.call(document.querySelectorAll('.ed'));
  q.addEventListener('input',function(){{
    var v=q.value.trim();
    eds.forEach(function(e){{
      e.hidden = !!v && e.dataset.n.indexOf(v)<0 && (e.dataset.d||'').indexOf(v)<0;
    }});
    document.querySelectorAll('.lang').forEach(function(s){{
      var any=s.querySelector('.ed:not([hidden])');
      s.style.display = any ? '' : 'none';
    }});
  }});
}})();
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
