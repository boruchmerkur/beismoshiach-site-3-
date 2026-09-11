# -*- coding: utf-8 -*-
"""Write science/codes/index.html — Codes in Nature, folded into Convergence.

The book is a print object: 24 nature cards, each pairing a shape found in the
world with a source that reads it. That is the same move Points of Convergence
makes six times, so the book belongs on this shelf rather than on a site of its
own — and here it is 24 more pairs, permanent ones, that do not need a wire to
refresh them.

Content comes from assets/codes.json, which is written out of the print layout
by codes-in-nature/extract_web.py. The print file is the source of truth and is
never edited from this side. Nothing in the Torah text is reworded here; the
prose is carried across verbatim, only the endnote anchors are rewritten to
point at this page.

    python3 tools/build_codes_page.py
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets", "codes.json")
OUT = os.path.join(ROOT, "science", "codes", "index.html")
ART = "/assets/science/codes/"

d = json.load(io.open(DATA, encoding="utf-8"))
CARDS = {c["slug"]: c for c in d["cards"]}


def art(filename):
    """Book filenames carry their print format; the web copies are all webp."""
    return ART + os.path.splitext(filename)[0] + ".webp"


def notes(html):
    """Point the book's endnote marks at this page's own endnote list."""
    return re.sub(r'href="#note-(\d+)"', r'href="#n\1"', html or "")


def card_html(slug, i):
    c = CARDS[slug]
    fig = ""
    if c["figure"]:
        fig = ('<p class="fig"><b>%s</b>%s</p>'
               % (c["figure"], " " + c["figure_label"] if c["figure_label"] else ""))
    mark = ('<img class="mark" loading="lazy" decoding="async" src="%s" alt="">'
            % art(c["inset"]) if c["inset"] else "")
    math = ('<p class="math">%s</p>' % notes(c["math_note"])) if c["math_note"] else ""

    dia = ""
    if c["diagram"]:
        cap = ('<figcaption>%s</figcaption>' % c["diagram"]["caption"]) if c["diagram"]["caption"] else ""
        dia = '<figure class="dia">%s%s</figure>' % (c["diagram"]["svg"], cap)

    return """
<article class="code%s" id="%s">
  <figure class="plate"><img loading="lazy" decoding="async" src="%s" alt="%s"></figure>
  <div class="code-body">
    <div class="code-head">%s<div><h3>%s</h3>%s</div></div>
    <div class="side sci">
      <p class="tag">The geometry</p>
      <div class="prose">%s</div>%s
    </div>%s
    <div class="side torah">
      <p class="tag">In the words of Torah</p>
      <div class="prose">%s</div>
    </div>
  </div>
</article>""" % (" flip" if i % 2 else "", c["slug"], art(c["plate"]),
                 c["plate_alt"] or c["title"], mark, c["title"], fig,
                 notes(c["nature"]), math, dia, notes(c["torah"]))


def section_html(s):
    dia = ""
    if s["diagram"]:
        cap = ""
        if s["diagram"]["caption"]:
            cap = '<figcaption>%s%s</figcaption>' % (
                s["diagram"]["caption"],
                " " + s["diagram"]["gloss"] if s["diagram"]["gloss"] else "")
        dia = '<figure class="dia wide">%s%s</figure>' % (s["diagram"]["svg"], cap)
    haiku = ""
    if s["haiku"]:
        haiku = '<p class="haiku">%s</p>' % "<br>".join(s["haiku"])
    banner = ('<figure class="banner"><img loading="lazy" decoding="async" src="%s" alt=""></figure>'
              % art(s["plate"])) if s["plate"] else ""
    math = ('<p class="math">%s</p>' % s["math_note"]) if s["math_note"] else ""
    body = "".join(card_html(slug, i) for i, slug in enumerate(s["cards"]))
    return """
<section class="band sec-band" id="%s"><div class="wrap">
  <p class="eyebrow">%s</p>
  <h2 class="sec">%s</h2>
  <p class="sec-sub">%s</p>
  %s
  <div class="epigraph">
    <p class="h">%s</p>
    <p class="en">%s</p>
    <p class="c">%s</p>
  </div>
  %s
  <div class="sec-intro"><p>%s</p>%s%s</div>
  %s
</div></section>""" % (
        re.sub(r"[^a-z0-9]+", "-", s["title"].lower()).strip("-"),
        s["num"], s["title"], s["sub"], banner,
        s["heb"], s["en"], s["src"], haiku, s["intro"], math, dia, body)


CONTENTS = "".join(
    '<div class="toc-col"><p class="toc-h">%s</p>%s</div>' % (
        s["title"],
        "".join('<a href="#%s">%s</a>' % (slug, CARDS[slug]["title"]) for slug in s["cards"]))
    for s in d["sections"])

ENDNOTES = "".join(
    '<li id="n%d"><span class="nn">%d</span>%s</li>' % (n, n, d["notes"][str(n)])
    for n in sorted(int(k) for k in d["notes"]))

GLOSSARY = "".join(
    '<div class="gl"><dt>%s</dt><dd>%s</dd></div>' % (g["term"], g["def"])
    for g in d["glossary"])

PAGE = r"""<!DOCTYPE html><html lang="en"><head>
<!-- pwa:start -->
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Beis Moshiach">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#0042AF">
<script defer src="/pwa.js"></script>
<!-- pwa:end -->
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Codes in Nature &mdash; Convergence | Beis Moshiach</title>
<meta name="description" content="Twenty-four shapes found in the world &mdash; the spiral, the hexagon, the branching of a river &mdash; each set beside the source that reads it. The Convergence shelf, in permanent form.">
<meta name="pwa-install-offset" content="66">
<link rel="canonical" href="https://beismoshiach.org/science/codes/">
<meta property="og:type" content="article"><meta property="og:site_name" content="beismoshiach.org">
<meta property="og:title" content="Codes in Nature">
<meta property="og:description" content="Twenty-four shapes found in the world, each set beside the source that reads it.">
<meta property="og:url" content="https://beismoshiach.org/science/codes/">
<meta property="og:image" content="https://beismoshiach.org__OG__">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,400&family=Geist:wght@300;400;500&family=JetBrains+Mono:wght@400;500&family=David+Libre:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<style>
  /* The shell — wrap, band, eyebrow, sec — is /science/'s, so the two pages
     read as one department. What is defined here is only what a book page
     needs and the wire page does not. */
  .wrap{max-width:1180px;margin:0 auto;padding:0 clamp(1rem,4vw,2.6rem)}
  .band{padding:clamp(2.2rem,6vw,4rem) 0;border-top:1px solid var(--rule)}
  .paper{background:var(--parchment-deep)}
  .eyebrow{font-family:var(--mono);font-size:.66rem;letter-spacing:.16em;text-transform:uppercase;
        color:var(--gold);margin:0 0 .9rem}
  h2.sec{font-family:var(--display);font-weight:600;font-size:clamp(1.5rem,3.4vw,2.2rem);margin:0 0 .5rem}
  .sec-sub{color:var(--ink-soft);max-width:70ch;margin:0 0 1.8rem}

  .hero{padding:clamp(2.4rem,7vw,4.6rem) 0 clamp(1.4rem,3vw,2.2rem)}
  .hero h1{font-family:var(--display);font-weight:900;font-size:clamp(2.3rem,6.5vw,4.2rem);line-height:1.02;
        margin:0 0 1rem;letter-spacing:-.02em}
  .hero .stand{font-size:clamp(1.02rem,1.9vw,1.2rem);line-height:1.55;color:var(--ink-soft);max-width:64ch;margin:0}
  .crumb{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
        color:var(--ink-soft);margin:0 0 1.1rem}
  .crumb a{color:var(--royal);text-decoration:none}

  /* Contents. Twenty-four cards is too many to scroll blind, and the print
     book has a contents page, so this one does too. */
  .toc{display:grid;grid-template-columns:repeat(4,1fr);gap:clamp(1rem,2.5vw,2rem)}
  @media(max-width:820px){.toc{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:460px){.toc{grid-template-columns:1fr}}
  .toc-h{font-family:var(--mono);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;
        color:var(--gold);margin:0 0 .6rem;padding-bottom:.5rem;border-bottom:1px solid var(--rule)}
  .toc-col a{display:block;padding:.3rem 0;font-size:.92rem;color:var(--ink);text-decoration:none}
  .toc-col a:hover{color:var(--royal)}

  .banner{margin:0 0 1.6rem;overflow:hidden;border-radius:3px}
  .banner img{display:block;width:100%;height:auto;aspect-ratio:21/9;object-fit:cover}
  .epigraph{max-width:60ch;margin:0 0 1.4rem;padding-left:1.1rem;border-left:2px solid var(--gold-bright)}
  .epigraph .h{font-family:var(--hebrew);font-size:1.3rem;line-height:1.8;direction:rtl;unicode-bidi:isolate;
        margin:0 0 .35rem;color:var(--ink)}
  .epigraph .en{font-size:.98rem;line-height:1.55;color:var(--ink-soft);margin:0 0 .3rem}
  .epigraph .c{font-family:var(--mono);font-size:.66rem;color:var(--ink-soft);margin:0}
  .haiku{font-family:var(--display);font-style:italic;font-size:1.02rem;line-height:1.7;
        color:var(--gold);margin:0 0 1.4rem}
  .sec-intro{max-width:74ch;margin:0 0 clamp(1.6rem,4vw,2.6rem)}
  .sec-intro p{margin:0 0 .8rem;line-height:1.65;color:var(--ink-soft)}

  /* A card: the plate on one side, the reading on the other, sides swapping
     down the page the way the recto/verso alternates in the printed book. */
  .code{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:clamp(1.2rem,3vw,2.4rem);
        align-items:start;padding:clamp(1.8rem,4vw,3rem) 0;border-top:1px solid var(--rule)}
  .code.flip .plate{order:2}
  @media(max-width:820px){.code{grid-template-columns:1fr}.code.flip .plate{order:0}}
  .code .plate{margin:0;overflow:hidden;border-radius:3px;position:sticky;top:5.5rem}
  @media(max-width:820px){.code .plate{position:static}}
  .code .plate img{display:block;width:100%;height:auto;aspect-ratio:2/3;object-fit:cover}
  .code-head{display:flex;align-items:center;gap:.9rem;margin:0 0 1.2rem}
  .code-head h3{font-family:var(--display);font-weight:600;font-size:clamp(1.3rem,2.6vw,1.8rem);
        margin:0;line-height:1.15}
  .mark{width:64px;height:64px;object-fit:contain;flex:0 0 auto}
  .fig{font-family:var(--mono);font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;
        color:var(--ink-soft);margin:.35rem 0 0}
  .fig b{color:var(--royal);font-weight:500;font-size:.95rem;letter-spacing:0;margin-right:.5rem}

  .side{margin:0 0 1.3rem}
  .side .tag{font-family:var(--mono);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;
        color:var(--ink-soft);margin:0 0 .5rem}
  .side.torah{border-top:1px solid var(--rule);padding-top:1.1rem}
  .side.torah .tag{color:var(--gold)}
  .prose{font-size:.99rem;line-height:1.68;color:var(--ink-soft)}
  .prose em{color:var(--ink);font-style:italic}
  .math{font-size:.9rem;line-height:1.6;color:var(--ink-soft);margin:.8rem 0 0;padding:.8rem 1rem;
        background:var(--royal-soft);border-radius:3px}
  sup a{color:var(--royal);text-decoration:none;font-size:.7em;padding:0 .1em}

  /* The diagrams are drawn in the book's own blue and gold on cream. Rather
     than recolour a figure that was made to be exact, each one keeps the paper
     it was drawn on — in dark mode too. */
  .dia{margin:0 0 1.3rem;background:#F3EAD8;border-radius:3px;padding:1rem 1.2rem}
  .dia svg{display:block;width:100%;max-width:340px;height:auto;margin:0 auto}
  .dia.wide svg{max-width:520px}
  .dia figcaption{font-size:.82rem;line-height:1.5;color:#5c5849;text-align:center;margin-top:.6rem}

  .endnotes ol{list-style:none;margin:0;padding:0;column-width:26rem;column-gap:2.6rem}
  .endnotes li{break-inside:avoid;margin:0 0 .8rem;font-size:.88rem;line-height:1.55;color:var(--ink-soft);
        padding-left:2rem;text-indent:-2rem}
  .endnotes .nn{font-family:var(--mono);font-size:.72rem;color:var(--royal);
        display:inline-block;width:2rem;text-indent:0}
  .endnotes li:target{color:var(--ink)}
  .endnotes li:target .nn{color:var(--oxblood)}
  .glossary{column-width:22rem;column-gap:2.6rem}
  .gl{break-inside:avoid;margin:0 0 .75rem}
  .gl dt{font-family:var(--display);font-weight:600;font-size:.98rem;color:var(--ink)}
  .gl dd{margin:.1rem 0 0;font-size:.88rem;line-height:1.55;color:var(--ink-soft)}

  .colofon-note{max-width:72ch;color:var(--ink-soft)}
  .colofon-note a{color:var(--royal)}
</style>
</head><body>

<header class="bm-topbar"><div class="bm-inner">
  <a class="bm-wordmark" href="/">beismoshiach<span class="bm-tld">.org</span></a>
  <nav><a href="/topics">Topics</a><a href="/parsha">Parsha</a><a href="/collections">Collections</a><a href="/science/">Convergence</a>
    <a href="/archives">Archives</a><a href="/search">Search</a><a class="langsw" href="/he/">עברית</a></nav>
</div></header>

<main>

<section class="hero"><div class="wrap">
  <p class="crumb"><a href="/science/">Convergence</a> &nbsp;&rsaquo;&nbsp; Codes in Nature</p>
  <p class="eyebrow">A book, on the shelf</p>
  <h1>Codes in Nature</h1>
  <p class="stand">Twenty&#8209;four shapes found in the world &mdash; the spiral of a shell, the six arms of a snowflake, the hexagon a bee builds without being taught it &mdash; each one measured, and each one set beside the source that reads it. Where the wire above is what arrived this morning, these are the pairs that do not change. Sixty endnotes carry the citations.</p>
</div></section>

<section class="band paper"><div class="wrap">
  <p class="eyebrow">Contents</p>
  <div class="toc">__CONTENTS__</div>
</div></section>

__SECTIONS__

<section class="band endnotes" id="endnotes"><div class="wrap">
  <p class="eyebrow">Every claim, sourced</p>
  <h2 class="sec">Endnotes</h2>
  <p class="sec-sub">The Torah teachings above are stated plainly, the way the book states them. Each one is answerable to a text, and the text is here.</p>
  <ol>__ENDNOTES__</ol>
</div></section>

<section class="band paper" id="glossary"><div class="wrap">
  <p class="eyebrow">The terms</p>
  <h2 class="sec">Glossary</h2>
  <div class="glossary">__GLOSSARY__</div>
</div></section>

<section class="band"><div class="wrap">
  <p class="eyebrow">About this shelf</p>
  <h2 class="sec">Where it sits</h2>
  <div class="colofon-note">
    <p><i>Codes in Nature &mdash; A Torah Companion</i> is a book of the <a href="/science/">Moshiach &amp; Science</a> department by another route. The wire on that page reads this morning's findings against six passages; this reads two dozen shapes that were in the world before anybody wrote anything down, against the sources that describe them. The argument is the same one, made slowly.</p>
    <p>The text and the artwork are from the printed edition, which is in preparation with The Tree of Life Books. A resemblance between a shape and a source is not a proof of anything, and none of the readings here are offered as though it were.</p>
  </div>
</div></section>

</main>

<footer class="colophon"><div class="wrap">
  <div class="cf-brand">beismoshiach.org</div>
  Codes in Nature &middot; twenty-four pairs, sixty sources.<br>
  <span style="opacity:.6">Part of <a href="/science/" style="color:inherit">Convergence</a>.</span>
</div></footer>

</body></html>
"""

sections = "".join(section_html(s) for s in d["sections"])
og = art(d["sections"][0]["plate"]) if d["sections"][0]["plate"] else ""
page = (PAGE.replace("__CONTENTS__", CONTENTS)
            .replace("__SECTIONS__", sections)
            .replace("__ENDNOTES__", ENDNOTES)
            .replace("__GLOSSARY__", GLOSSARY)
            .replace("__OG__", og))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write(page)
print("wrote %s  (%.0f KB)  %d sections, %d cards, %d endnotes, %d glossary"
      % (OUT, len(page) / 1024, len(d["sections"]), len(d["cards"]),
         len(d["notes"]), len(d["glossary"])))
