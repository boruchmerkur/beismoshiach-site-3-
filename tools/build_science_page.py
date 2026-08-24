# -*- coding: utf-8 -*-
"""Write science/index.html — the Convergence material, folded into the magazine.

The standalone site is retired. What moves here is everything that was worth
keeping: the six readings, the 1840 timeline, and the live wire. What is NEW is
that the archive's own Moshiach & Science department sits in the same grid as
the wire, in the same card, so a piece from issue #1033 and a paper published
this morning are the same kind of object on the page.

The static sections (timeline, readings) are lifted out of the old build and
pasted in verbatim — they are prose and artwork that were already right.

Re-run after tools/build_science.py:  python3 tools/build_science_page.py
"""
import io, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = os.environ.get("CONV_SECTIONS") or os.path.join(ROOT, "tools", "sections.html")
OUT = os.path.join(ROOT, "science", "index.html")

raw = io.open(SECTIONS, encoding="utf-8").read()
TIMELINE = raw.split("<!--TIMELINE-->")[1].split("<!--NOTE-->")[0].strip()
NOTE = raw.split("<!--NOTE-->")[1].split("<!--PAIRS-->")[0].strip()
PAIRS = raw.split("<!--PAIRS-->")[1].strip()


def bake_plates(tl):
    """Put the 26 timeline drawings into the markup instead of injecting them.

    The old build appended them from a JS array at runtime. Baking them in at
    build time means they are in the HTML a crawler sees and they survive with
    JavaScript off — and this page is generated anyway, so there is no reason
    to do at runtime what can be done here. SVG is served directly and never
    through the image CDN, which would raster it and make it larger.
    """
    n = [0]

    def add(m):
        year = m.group(1)
        svg = os.path.join(ROOT, "assets", "science", "tl-%s.svg" % year)
        if not os.path.isfile(svg):
            return m.group(0)
        n[0] += 1
        return (m.group(0) +
                '\n        <figure class="ev-art">'
                '<img loading="lazy" decoding="async" src="/assets/science/tl-%s.svg" alt=""></figure>'
                % year)

    tl = re.sub(r'<li data-year="([^"]+)"[^>]*>', add, tl)
    print("timeline plates baked in:", n[0])
    return tl


TIMELINE = bake_plates(TIMELINE)

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
<title>Convergence &mdash; Moshiach &amp; Science | Beis Moshiach</title>
<meta name="description" content="The magazine's Moshiach &amp; Science writing, read alongside a live wire of scientific discovery, and both sorted against six readings from the sources.">
<meta name="pwa-install-offset" content="66">
<link rel="canonical" href="https://beismoshiach.org/science/">
<meta property="og:type" content="website"><meta property="og:site_name" content="beismoshiach.org">
<meta property="og:title" content="Convergence &mdash; Moshiach &amp; Science">
<meta property="og:description" content="The archive's science writing beside a live wire of discovery, sorted against six readings from the sources.">
<meta property="og:url" content="https://beismoshiach.org/science/">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,400&family=Geist:wght@300;400;500&family=JetBrains+Mono:wght@400;500&family=David+Libre:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<style>
  /* The card, the row and the chip are the landing page's, verbatim, because a
     wire story and an archive piece have to be the same object here. Only what
     this page adds is defined below. */
  .wrap{max-width:1180px;margin:0 auto;padding:0 clamp(1rem,4vw,2.6rem)}
  .row{display:grid;align-items:start;grid-template-columns:repeat(3,1fr);gap:clamp(1rem,2.5vw,1.8rem);
       padding-bottom:clamp(2rem,5vw,3.5rem)}
  @media(max-width:900px){.row{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:560px){.row{grid-template-columns:1fr}}
  .card{display:block;color:inherit;text-decoration:none}
  .card figure{margin:0 0 .8rem;overflow:hidden;border-radius:3px;background:var(--parchment-deep)}
  .card img{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:cover;object-position:center;
        background:var(--parchment-deep);transition:transform .7s var(--ease)}
  .card:hover img{transform:scale(1.05)}
  .card h3{font-family:var(--display);font-weight:600;font-size:1.12rem;line-height:1.25;margin:0 0 .4rem;color:var(--ink)}
  .card:hover h3{color:var(--royal)}
  .card .blurb{font-size:.9rem;line-height:1.55;color:var(--ink-soft);margin:0 0 .55rem;
        display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;line-clamp:3;overflow:hidden}
  .card.txt .blurb{-webkit-line-clamp:7;line-clamp:7;font-size:.94rem;margin-bottom:.8rem}
  @media(max-width:560px){.card .blurb{-webkit-line-clamp:4;line-clamp:4}}
  .card.txt{display:flex;flex-direction:column;justify-content:center;align-self:start;
        padding:1.1rem 1.2rem;background:var(--parchment-deep);border:1px solid var(--parchment-edge);
        border-left:3px solid var(--gold-bright);border-radius:3px;transition:border-color .2s,transform .3s var(--ease)}
  .card.txt:hover{transform:translateY(-2px);border-color:var(--royal);border-left-color:var(--royal)}
  .card.txt h3{font-size:1.3rem}
  .card .meta{font-family:var(--mono);font-size:.68rem;letter-spacing:.03em;color:var(--ink-soft);margin:0}
  .why{display:inline-block;font-family:var(--mono);font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;
        color:var(--royal);background:var(--royal-soft);border-radius:2px;padding:.28rem .5rem;margin:0 0 .5rem}
  .why.plain{color:var(--ink-soft);background:transparent;padding-left:0}

  /* THE ONE THING THAT TELLS THE TWO APART. A wire story is somebody else's and
     leaves the site; an archive piece is ours. Rather than two card designs,
     the wire card carries a hairline top rule and its source in the chip, so
     the reader can see which is which without the grid breaking into two. */
  .card.wire figure{border-top:2px solid var(--gold-bright)}
  .card.wire.txt{border-left-color:var(--ink-soft)}
  .card .he{font-family:var(--hebrew);font-size:.95rem;color:var(--gold);direction:rtl;unicode-bidi:isolate;
        display:block;margin:.1rem 0 .45rem}

  .hero{padding:clamp(1.6rem,3.5vw,2.4rem) 0 clamp(1rem,2vw,1.4rem)}
  .hero h1{font-family:var(--display);font-weight:900;font-size:clamp(2.3rem,6.5vw,4.2rem);line-height:1.02;
        margin:0 0 1rem;letter-spacing:-.02em}
  .hero .stand{font-size:clamp(1.02rem,1.9vw,1.2rem);line-height:1.55;color:var(--ink-soft);max-width:64ch;margin:0}
  .eyebrow{font-family:var(--mono);font-size:.66rem;letter-spacing:.16em;text-transform:uppercase;
        color:var(--gold);margin:0 0 .9rem}
  h2.sec{font-family:var(--display);font-weight:600;font-size:clamp(1.5rem,3.4vw,2.2rem);margin:0 0 .5rem}
  .sec-sub{color:var(--ink-soft);max-width:70ch;margin:0 0 1.8rem}
  .band{padding:clamp(2.2rem,6vw,4rem) 0;border-top:1px solid var(--rule)}
  /* A band after the hero was adding its own 64px top padding and a rule to the
     hero's 35px bottom padding: 100px of nothing between the standfirst and the
     filters, and the first card pushed to 520px down a 720px screen. The gap
     between two SECTIONS is worth having; the gap between a title and the thing
     it titles is not. */
  .hero + .band{padding-top:clamp(.9rem,2vw,1.5rem);border-top:0}
  .paper{background:var(--parchment-deep)}

  .filters{display:flex;flex-wrap:wrap;gap:.55rem;padding-bottom:1.6rem}
  .filters button{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;
        border:1px solid var(--parchment-edge);background:transparent;border-radius:999px;padding:.55rem 1rem;
        color:var(--ink);cursor:pointer;transition:border-color .2s,color .2s,background .2s}
  .filters button:hover{border-color:var(--gold-bright)}
  .filters button[aria-pressed=true]{border-color:var(--royal);color:var(--royal);background:var(--royal-soft)}
  .state{font-family:var(--mono);font-size:.78rem;color:var(--ink-soft);padding:.4rem 0 1.4rem}
  .more{display:block;margin:0 auto clamp(2rem,5vw,3rem);font-family:var(--mono);font-size:.74rem;
        letter-spacing:.08em;text-transform:uppercase;border:1px solid var(--parchment-edge);background:transparent;
        border-radius:999px;padding:.7rem 1.6rem;color:var(--ink);cursor:pointer}
  .more:hover{border-color:var(--royal);color:var(--royal)}
  .briefs{border-top:1px solid var(--rule);padding-top:1.4rem}
  .briefs a{display:block;padding:.62rem 0;border-bottom:1px solid var(--rule);color:inherit;text-decoration:none}
  .briefs a:hover{color:var(--royal)}
  .briefs .bt{font-family:var(--display);font-size:1rem}
  .briefs .bm{font-family:var(--mono);font-size:.66rem;color:var(--ink-soft)}

  /* ---- the 1840 timeline, carried over ---- */
  .tl{list-style:none;margin:0;padding:0;position:relative}
  .tl:before{content:"";position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--rule)}
  .tl .ev{position:relative;width:calc(50% - 2.2rem);padding:1rem 0 1.6rem}
  .tl .ev.torah{margin-right:auto;text-align:right}
  .tl .ev.science{margin-left:auto}
  .tl .yr{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;color:var(--gold)}
  .tl .ev.science .yr{color:var(--royal)}
  .tl h4{font-family:var(--display);font-weight:600;font-size:1.06rem;margin:.25rem 0 .3rem}
  .tl p{margin:0;font-size:.92rem;line-height:1.55;color:var(--ink-soft)}
  .tl .ev-art{margin:0 0 .7rem}
  .tl .ev img{width:100%;max-width:230px;height:auto;border-radius:2px;display:block}
  .tl .ev.torah img{margin-left:auto}
  @media(max-width:760px){
    .tl:before{left:6px}
    .tl .ev,.tl .ev.torah,.tl .ev.science{width:auto;margin:0 0 0 1.8rem;text-align:left}
    .tl .ev.torah img{margin-left:0}
  }
  .charter-note{margin-top:1.4rem;padding-top:1.2rem;border-top:1px solid var(--rule);
        font-size:.92rem;color:var(--ink-soft);max-width:72ch}

  /* ---- the six readings, carried over ---- */
  .pair{padding:clamp(1.6rem,4vw,2.6rem) 0;border-bottom:1px solid var(--rule)}
  .pair:last-of-type{border-bottom:0}
  .pair .plate{margin:0 0 1.2rem;overflow:hidden;border-radius:3px}
  .pair .plate img{display:block;width:100%;height:auto;aspect-ratio:21/9;object-fit:cover}
  .pair-cols{display:grid;grid-template-columns:1fr 1px 1fr;gap:clamp(1rem,3vw,2.2rem);align-items:start}
  @media(max-width:820px){.pair-cols{grid-template-columns:1fr}.joint{display:none}}
  .joint{background:var(--rule)}
  .side .tag{font-family:var(--mono);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-soft)}
  .side.torah .tag{color:var(--gold)}
  .side .h{font-family:var(--hebrew);font-size:1.35rem;line-height:1.7;direction:rtl;unicode-bidi:isolate;
        margin:.5rem 0 .6rem;color:var(--ink)}
  .side p{margin:0 0 .5rem;font-size:.96rem;line-height:1.6;color:var(--ink-soft)}
  .side .c{font-family:var(--mono);font-size:.66rem;color:var(--ink-soft)}

  .lineage{max-width:72ch}
  .lineage p{color:var(--ink-soft)}
  .lineage cite{font-style:normal;color:var(--ink)}
  .lineage a{color:var(--royal)}
  @media (prefers-reduced-motion:no-preference){
    .reveal{animation:fade .7s var(--ease) both}
    @keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
  }
</style>
</head><body>

<header class="bm-topbar"><div class="bm-inner">
  <a class="bm-wordmark" href="/">beismoshiach<span class="bm-tld">.org</span></a>
  <nav><a href="/topics">Topics</a><a href="/parsha">Parsha</a><a href="/collections">Collections</a><a href="/science/">Convergence</a>
    <a href="/archives">Archives</a><a href="/search">Search</a><a class="langsw" href="/he/">עברית</a></nav>
</div></header>

<main>

<section class="hero"><div class="wrap">
  <p class="eyebrow">Moshiach &amp; Science</p>
  <h1>Convergence</h1>
  <p class="stand">A live wire. <b>Nature</b>, <b>Quanta</b>, <b>New&nbsp;Scientist</b>, <b>Science&nbsp;News</b>, <b>ScienceDaily</b>, <b>Live&nbsp;Science</b>, <b>Ars&nbsp;Technica</b>, <b>Phys.org</b> and <b>NASA</b> carry the discoveries; <b>Chabad.org</b>, <b>Anash</b>, <b>COLlive</b>, <b>CrownHeights.info</b> and <b>Moshiach101</b> carry the news from our own world.</p>
</div></section>

<section class="band" id="wire"><div class="wrap">
  <div class="filters" id="filters">
    <button data-f="all" aria-pressed="true">Everything</button>
    <button data-f="archive" aria-pressed="false">From the archive</button>
    <button data-f="wire" aria-pressed="false">From the wire</button>
    <button data-f="matched" aria-pressed="false">Reads against a source</button>
  </div>
  <div class="row" id="grid"></div>
  <p class="state" id="state">Gathering the wire&hellip;</p>
  <button class="more" id="more" hidden>Show more</button>
  <div class="briefs" id="briefs" hidden>
    <p class="eyebrow" style="color:var(--ink-soft)">In brief &mdash; <span id="briefs-n"></span> without pictures</p>
    <div id="briefs-list"></div>
  </div>
</div></section>

<section class="band charter"><div class="wrap">
  <p class="eyebrow">The year named in the text</p>
  <h2 class="sec">1840, and what came after</h2>
  <p class="sec-sub">The Zohar puts a date on it: the six-hundredth year of the sixth millennium, which is 5600, which is 1840. Two openings, not one &mdash; wisdom above and wellsprings below. Here are both tracks against the same spine.</p>
  __TIMELINE__
  <p class="charter-note">__NOTE__</p>
</div></section>

<section class="band paper" id="points"><div class="wrap">
  <p class="eyebrow">Six readings</p>
  <h2 class="sec">Points of Convergence</h2>
  <p class="sec-sub">The source on the left, the finding on the right, meeting in the middle. These are the six readings everything above is sorted against.</p>
  __PAIRS__
</div></section>

<section class="band" id="codes"><div class="wrap">
  <p class="eyebrow">On the shelf</p>
  <h2 class="sec">Codes in Nature</h2>
  <p class="sec-sub">The wire is what arrived this morning. This is the part that does not move: twenty&#8209;four shapes found in the world &mdash; the spiral of a shell, the six arms of a snowflake, the hexagon a bee builds without being taught it &mdash; each measured, and each set beside the source that reads it. A book, on the page.</p>
  <div class="row">
    <a class="card txt" href="/science/codes/">
      <span class="why plain">24 pairs &middot; 60 sources</span>
      <h3>Read it here</h3>
      <p class="blurb">Four sections &mdash; the spiral, symmetry, fractals, and the shapes that keep things alive &mdash; with the geometry stated plainly, the mathematics kept to one note, and the Torah reading answerable to an endnote every time.</p>
      <p class="meta">Codes in Nature &mdash; A Torah Companion</p>
    </a>
    <a class="card" href="/science/codes/#snowflake">
      <figure><img loading="lazy" decoding="async" src="/assets/science/codes/image_021.webp" alt=""></figure>
      <h3>One law, infinite expressions</h3>
      <p class="blurb">Six arms, every time, and no two crystals alike &mdash; the constraint and the freedom arriving together.</p>
    </a>
    <a class="card" href="/science/codes/#honeycomb">
      <figure><img loading="lazy" decoding="async" src="/assets/science/codes/image_039.webp" alt=""></figure>
      <h3>Maximum storage, minimum wax</h3>
      <p class="blurb">The hexagon is the answer to a problem no bee has ever been told it is solving.</p>
    </a>
  </div>
</div></section>

<section class="band" id="lineage"><div class="wrap lineage">
  <p class="eyebrow">Where the name comes from</p>
  <h2 class="sec">Convergence</h2>
  <p>The word is not ours. It is the title of the first appendix to <cite>Mind Over Matter: The Lubavitcher Rebbe on Science, Technology and Medicine</cite> &mdash; <a href="https://www.chabad.org/library/article_cdo/aid/113102/jewish/Appendix-1-FaithScience-Convergence-Explained.htm" rel="noopener">Faith/Science Convergence Explained</a>, by Rabbi Joseph Ginsburg and Prof.&nbsp;Herman Branover, edited by Dr.&nbsp;Arnie Gotfryd.</p>
  <p>That appendix sets out the claim this page is built on: that the principles of religion and the findings of natural science do not merely avoid conflict but line up &mdash; and that the lining-up is itself one of the signs the sources describe. The six readings below the wire are that argument given six specific pairs to stand on.</p>
  <p>Beis Moshiach has been in this lineage for a long time. Issue&nbsp;#1089 carries a talk of the Rebbe under the title <a href="/articles/modern-science-as-a-prelude-to-moshiach.html">Modern Science as a Prelude to Moshiach</a>, reprinted with permission from that same book. Prof.&nbsp;Branover appears throughout the archive &mdash; and Dr.&nbsp;Gotfryd's own work in the magazine runs from <a href="/articles/shliach-to-academia.html">Shliach to Academia</a> (#950) onward. Prof.&nbsp;Shimon Silman wrote the department for years; his nine pieces are in the grid above.</p>
  <p style="margin-top:1.4rem;padding-top:1.2rem;border-top:1px solid var(--rule);font-size:.92rem">The wire pulls from thirteen public feeds and is filtered server-side; a story from a general-interest source is admitted only on a concrete scientific term. The dates in the timeline are dates set beside dates. None of it demonstrates that one thing caused another, and it is not offered as though it did.</p>
</div></section>

</main>

<footer class="colophon"><div class="wrap">
  <div class="cf-brand">beismoshiach.org</div>
  Moshiach &amp; Science &middot; the department, the wire, six readings, and <a href="/science/codes/" style="color:inherit">a book</a>.<br>
  <span style="opacity:.6">Sources named on every card.</span>
</div></footer>

<script>
(function(){
  'use strict';
  var PAGE = 12, shown = PAGE, filter = 'all', pool = [], wireOk = false;
  var grid = document.getElementById('grid'), state = document.getElementById('state'),
      more = document.getElementById('more'), briefs = document.getElementById('briefs'),
      blist = document.getElementById('briefs-list'), bn = document.getElementById('briefs-n');

  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }

  function ago(ts){
    if(!ts) return '';
    var m = Math.round((Date.now()-ts)/60000);
    if(m < 60) return m + 'm ago';
    if(m < 1440) return Math.round(m/60) + 'h ago';
    return Math.round(m/1440) + 'd ago';
  }

  /* Netlify's Image CDN at the size the slot needs. The host must also be in
     [images] remote_images in netlify.toml or this 400s. */
  function cdn(u, w){
    return '/.netlify/images?url=' + encodeURIComponent(u) + '&w=' + w + '&fm=webp&q=76';
  }
  window.imgFallback = function(el){
    var a = el.getAttribute('data-a'), b = el.getAttribute('data-b');
    if(a){ el.removeAttribute('data-a'); el.src = a; return; }
    if(b){ el.removeAttribute('data-b'); el.src = b; return; }
    var fig = el.closest('figure'); if(fig) fig.remove();
  };

  function card(it){
    var cls = 'card' + (it.kind === 'wire' ? ' wire' : '') + (it.img ? '' : ' txt');
    var open = it.kind === 'wire'
      ? '<a class="' + cls + '" href="' + esc(it.link) + '" target="_blank" rel="noopener">'
      : '<a class="' + cls + '" href="/articles/' + esc(it.s) + '.html">';
    var pic = '';
    if(it.img){
      pic = it.kind === 'wire'
        ? '<figure><img loading="lazy" decoding="async" referrerpolicy="no-referrer" alt=""' +
          ' src="' + esc(cdn(it.img, 640)) + '" data-a="' + esc(it.img) + '"' +
          (it.imgRaw ? ' data-b="' + esc(it.imgRaw) + '"' : '') +
          ' onerror="imgFallback(this)"></figure>'
        : '<figure><img loading="lazy" decoding="async" alt="" src="/' + esc(it.img) + '"></figure>';
    }
    var chip = it.read
      ? '<span class="why">' + esc(it.read.c) + '</span>'
      : '<span class="why plain">' + esc(it.kind === 'wire' ? it.src : (it.dept || 'Beis Moshiach')) + '</span>';
    var he = it.read ? '<span class="he">' + esc(it.read.h) + '</span>' : '';
    var meta = it.kind === 'wire'
      ? esc(it.src) + ' &middot; ' + esc(ago(it.ts))
      : esc([it.a, it.dept, it.iss ? '#' + it.iss : ''].filter(Boolean).join(' · '));
    return open + pic + chip + '<h3>' + esc(it.t) + '</h3>' + he +
      '<p class="blurb">' + esc(it.blurb) + '</p>' +
      '<p class="meta">' + meta + '</p></a>';
  }

  function pass(it){
    if(filter === 'all') return true;
    if(filter === 'matched') return !!it.read;
    return it.kind === filter;
  }

  function render(){
    var keep = pool.filter(pass);
    var without = keep.filter(function(i){ return !i.img && i.kind === 'wire'; });
    /* An archive piece without a picture still gets a card: it is ours, it is
       edited, and the type card was built for exactly that. Only a wire story
       with no photograph drops to the list. */
    var cards = keep.filter(function(i){ return i.img || i.kind === 'archive'; });
    /* Weave AFTER that filter, not before. Weaving the whole pool and then
       removing the picture-less wire stories collapses the gaps and the every-
       third-card rhythm drifts — which is what it did on the first build. */
    cards = weave(cards.filter(function(i){ return i.kind === 'archive'; }),
                  cards.filter(function(i){ return i.kind === 'wire'; }));

    grid.innerHTML = cards.slice(0, shown).map(card).join('');
    more.hidden = cards.length <= shown;
    state.hidden = true;

    if(without.length){
      briefs.hidden = false;
      bn.textContent = without.length;
      blist.innerHTML = without.map(function(i){
        return '<a href="' + esc(i.link) + '" target="_blank" rel="noopener">' +
          '<span class="bt">' + esc(i.t) + '</span><br>' +
          '<span class="bm">' + esc(i.src) + (i.read ? ' &middot; ' + esc(i.read.c) : '') +
          ' &middot; ' + esc(ago(i.ts)) + '</span></a>';
      }).join('');
    } else {
      /* Clear it, don't just hide it. A hidden list of 26 links is still 26
         links in the accessibility tree. */
      briefs.hidden = true; blist.innerHTML = '';
    }
  }

  /* THE INTERLEAVE. The wire refreshes and the archive does not, so a plain
     date sort would bury thirty-three edited pieces under whatever was
     published this morning — which is the wrong way round for a magazine.
     Every third card is an archive piece until the archive runs out. */
  function weave(arch, wire){
    var out = [], a = 0, w = 0;
    while(a < arch.length || w < wire.length){
      if(out.length % 3 === 2 && a < arch.length) out.push(arch[a++]);
      else if(w < wire.length) out.push(wire[w++]);
      else if(a < arch.length) out.push(arch[a++]);
      else break;
    }
    return out;
  }

  document.getElementById('filters').addEventListener('click', function(e){
    var b = e.target.closest('button[data-f]'); if(!b) return;
    filter = b.dataset.f; shown = PAGE;
    [].forEach.call(this.querySelectorAll('button'), function(x){
      x.setAttribute('aria-pressed', String(x === b)); });
    render();
  });
  more.addEventListener('click', function(){ shown += PAGE; render(); });

  var archP = fetch('/assets/science.json?v=' + Date.now()).then(function(r){ return r.json(); })
    .catch(function(){ return { items: [] }; });
  var wireP = fetch('/api/wire').then(function(r){ return r.json(); })
    .catch(function(){ return null; });

  Promise.all([archP, wireP]).then(function(res){
    var arch = (res[0].items || []).map(function(a){
      a.kind = 'archive'; return a;
    });
    var w = res[1];
    wireOk = !!(w && w.items);
    var wire = wireOk ? w.items.map(function(i){
      return { kind:'wire', t:i.title, blurb:i.sum, link:i.link, img:i.img,
               imgRaw:i.imgRaw, ts:i.ts, src:i.src, read:i.read };
    }) : [];
    pool = arch.concat(wire);   /* order is decided in render(), after filtering */
    if(!wireOk){
      state.hidden = false;
      state.textContent = 'The wire is not answering; the archive is below.';
    }
    render();
    if(!wireOk) state.hidden = false;
  });
})();
</script>
</body></html>
"""

page = (PAGE.replace("__TIMELINE__", TIMELINE)
            .replace("__NOTE__", NOTE)
            .replace("__PAIRS__", PAIRS))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, "w", encoding="utf-8").write(page)
print("science/index.html: %d bytes (%d timeline entries, %d readings)" % (
    len(page), TIMELINE.count("<li "), PAIRS.count('<article class="pair">')))
