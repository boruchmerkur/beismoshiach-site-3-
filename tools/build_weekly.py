# -*- coding: utf-8 -*-
"""Build the beismoshiach.org weekly landing page from the existing archive.

The archive is timeless: the same parsha and the same Chabad dates come round
every year, so a piece from issue #874 reads as current in its week. This
script indexes what we already have, precomputes which tags belong to which
week for the next several years, and writes:

    assets/weekly.json   the index + the schedule
    index.html           the landing page, with THIS week rendered into the
                         HTML (so it is right with JavaScript switched off)
                         plus a small script that re-picks from the visitor's
                         own date, so the page keeps itself current forever.

Re-run only when new articles are added:  python3 tools/build_weekly.py
"""
import os, re, json, html, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "articles")
TAGS = os.path.join(ART, "tag")
YEARS = 6  # weeks of schedule to precompute

# ---------------------------------------------------------------- article index
CACHE_RE = re.compile(r"@__SQUARESPACE_CACHEVERSION=\d+")

def clean_img(src):
    """Normalise the export's doubled-up paths and cache suffixes to a real file."""
    if not src:
        return None
    src = CACHE_RE.sub("", html.unescape(src)).strip()
    src = src.replace("../storage/../storage/", "storage/")
    src = re.sub(r"^\.\./", "", src)
    src = re.sub(r"^/", "", src)
    if not src.startswith("storage/"):
        i = src.find("storage/")
        if i >= 0:
            src = src[i:]
        else:
            return None
    return src if os.path.isfile(os.path.join(ROOT, src.replace("/", os.sep))) else None

def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ").strip()

def read_article(slug):
    p = os.path.join(ART, slug + ".html")
    if not os.path.isfile(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r'<h1 class="entry-title">(.*?)</h1>', t, re.S)
    title = strip(m.group(1)) if m else slug.replace("-", " ").title()
    au = re.search(r'class="au">([^<]+)<', t)
    dept = re.search(r'class="dept"[^>]*>([^<]+)<', t)
    iss = re.search(r'href="tag/(\d+)\.html"', t)
    desc = re.search(r'<meta name="description" content="([^"]*)"', t)
    img = re.search(r'<div class="entry-body">.*?<img[^>]+src="([^"]+)"', t, re.S)
    summ = strip(desc.group(1)) if desc else ""
    return {
        "s": slug,
        "t": title,
        "a": strip(au.group(1)) if au else "",
        "c": strip(dept.group(1)) if dept else "",
        "i": int(iss.group(1)) if iss else None,
        "d": (summ[:190] + "…") if len(summ) > 190 else summ,
        "img": clean_img(img.group(1)) if img else None,
    }

def looks_broken(a):
    """Some export titles are body text or the 'Recent Articles' shell."""
    t = a["t"]
    return (t.startswith("Beis Moshiach Magazine") or len(t) > 72 or
            t.lower().startswith(("translated ", "by ")) or not t)

# ------------------------------------------------------------------ tag sources
def from_parsha_page():
    out = {}
    p = os.path.join(ROOT, "parsha.html")
    if not os.path.isfile(p):
        return out
    t = open(p, encoding="utf-8", errors="replace").read()
    for slug, _name, _n, body in re.findall(
        r'<h2 class="grp" id="([^"]+)">(.*?)<span class="gc">(\d+)</span></h2>\s*<ul class="artlist">(.*?)</ul>',
        t, re.S):
        out.setdefault(slug, [])
        for href in re.findall(r'<a class="lt" href="articles/([a-z0-9\-]+)\.html"', body):
            if href not in out[slug]:
                out[slug].append(href)
    return out

def from_tag_pages():
    out = {}
    if not os.path.isdir(TAGS):
        return out
    for f in os.listdir(TAGS):
        if not f.endswith(".html"):
            continue
        slug = f[:-5]
        if slug.isdigit():           # issue tags, not topical
            continue
        t = open(os.path.join(TAGS, f), encoding="utf-8", errors="replace").read()
        hits = re.findall(r'<a class="lt" href="\.\./([a-z0-9\-]+)\.html"', t)
        if hits:
            out[slug] = hits
    return out

# --------------------------------------------------- calendar name -> site slug
def norm(s):
    return re.sub(r"[^a-z]", "", s.lower())

PARSHA_ALIASES = {
    # pyluach name -> candidate site slugs, best first
    "Re'eh": ["rei", "r-ei", "re-eh", "reeh", "parshas-reeh"],
    "Va'eschanan": ["va-eschanan", "vaeschanan", "vaes-chanan"],
    "Va'eira": ["va-eira", "vaeira"],
    "Chayei Sarah": ["chayei-sara", "chayei-sarah"],
    "Shemos": ["shmos", "shemos"], "Shemini": ["shmini", "shemini"],
    "Shelach": ["shlach", "shelach"], "Nasso": ["naso", "nasso"],
    "Beha'aloscha": ["b-haalos-cha", "behaaloscha", "b-haaloscha"],
    "Haazinu": ["ha-azinu", "haazinu"],
    "Acharei Mos": ["acharei", "acharei-mos"],
    "Mattos, Masei": ["masei", "matos-masei", "mattos-masei"],
    "Nitzavim, Vayeilech": ["nitzavim-vayeilech", "nitzavim", "vayeilech"],
    "Chukas, Balak": ["chukas", "balak"],
    "Tazria, Metzora": ["tazria", "metzora"],
    "Acharei Mos, Kedoshim": ["acharei", "kedoshim"],
    "Behar, Bechukosai": ["behar", "bechukosai"],
    "Vayakhel, Pekudei": ["vayakhel", "pekudei"],
}

# Hebrew-date driven occasions: (month, day) -> site slugs, best first
OCCASIONS = {
    (7, 1): ["rosh-hashanah", "rosh-hashana"], (7, 10): ["yom-kippur"],
    (7, 15): ["sukkos"], (7, 22): ["simchas-torah"],
    (9, 19): ["yud-tes-kislev"], (9, 25): ["chanukah"],
    (11, 10): ["yud-shvat", "basi-l-gani"], (11, 15): ["tu-b-shvat"],
    (11, 22): ["chof-beis-shvat"],
    (12, 14): ["purim"], (1, 2): ["beis-nissan"], (1, 11): ["yud-alef-nissan"],
    (1, 15): ["pesach"], (2, 18): ["lag-baomer", "lag-bomer"],
    (3, 6): ["shavuos"], (4, 12): ["yud-beis-tammuz"], (4, 3): ["gimmel-tammuz"],
    (5, 9): ["tisha-b-av"], (6, 18): ["chai-elul"],
}
MONTH_TAGS = {5: ["menachem-av"], 6: ["elul"], 7: ["tishrei"]}

def pick_slug(cands, index):
    for c in cands:
        if index.get(c):
            return c
    return None

# ----------------------------------------------------------------------- build
def main():
    try:
        from pyluach import dates, parshios
    except ImportError:
        sys.exit("pyluach is required:  python3 -m pip install pyluach")

    tagmap = from_parsha_page()
    for k, v in from_tag_pages().items():       # merge; parsha.html is richer where it exists
        tagmap.setdefault(k, [])
        for s in v:
            if s not in tagmap[k]:
                tagmap[k].append(s)

    # ---- schedule: every Shabbos for the next YEARS years
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday() + 2 if today.weekday() < 5 else 0)
    sched, need = [], set()
    day = today - datetime.timedelta(days=14)
    end = today + datetime.timedelta(days=365 * YEARS)
    seen_weeks = set()
    while day <= end:
        sat = day + datetime.timedelta((5 - day.weekday()) % 7)
        if sat in seen_weeks:
            day += datetime.timedelta(days=7); continue
        seen_weeks.add(sat)
        hd = dates.GregorianDate(sat.year, sat.month, sat.day)
        pname = parshios.getparsha_string(hd, israel=False)
        tags = []
        if pname:
            cands = PARSHA_ALIASES.get(pname) or []
            cands = cands + [norm(pname), re.sub(r"[^a-z]+", "-", pname.lower()).strip("-")]
            sl = pick_slug(cands, tagmap)
            if sl:
                tags.append(sl)
        # occasions + month falling anywhere in this week
        for off in range(-6, 1):
            d2 = sat + datetime.timedelta(days=off)
            h2 = dates.GregorianDate(d2.year, d2.month, d2.day).to_heb()
            for cands in [OCCASIONS.get((h2.month, h2.day))]:
                if cands:
                    sl = pick_slug(cands, tagmap)
                    if sl and sl not in tags:
                        tags.append(sl)
        hsat = hd.to_heb()
        for cands in [MONTH_TAGS.get(hsat.month)]:
            if cands:
                sl = pick_slug(cands, tagmap)
                if sl and sl not in tags:
                    tags.append(sl)
        sched.append({"w": sat.isoformat(), "p": pname or "", "tags": tags,
                      "hd": "%d %s %d" % (hsat.day, hsat.month_name(), hsat.year)})
        for t in tags:
            need.update(tagmap.get(t, [])[:14])
        day += datetime.timedelta(days=7)

    # ---- evergreen pool: strong, always-relevant departments
    ever = []
    for t in ["moshiach-geula", "chai-vkayam", "beis-hamikdash", "igrot-kodesh",
              "rebbe", "miracle-story", "chinuch", "shleimus-ha-aretz"]:
        for s in tagmap.get(t, [])[:12]:
            if s not in ever:
                ever.append(s)
    need.update(ever)

    # ---- resolve articles
    arts = {}
    for s in sorted(need):
        a = read_article(s)
        if a and not looks_broken(a):
            arts[s] = a
    # drop dead references
    for t in list(tagmap):
        tagmap[t] = [s for s in tagmap[t] if s in arts][:14]
    ever = [s for s in ever if s in arts]

    keep = {t: v for t, v in tagmap.items() if v}
    data = {"built": today.isoformat(), "articles": arts, "tags": keep,
            "evergreen": ever, "schedule": sched}
    outp = os.path.join(ROOT, "assets", "weekly.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("weekly.json: %d articles, %d tags, %d weeks (%.0f KB)"
          % (len(arts), len(keep), len(sched), os.path.getsize(outp) / 1024))
    render_landing(data)
    return data

# --------------------------------------------------------------------- landing
def week_for(data, today=None):
    today = today or datetime.date.today()
    for w in data["schedule"]:
        if datetime.date.fromisoformat(w["w"]) >= today:
            return w
    return data["schedule"][-1]

def pick(data, wk, n=7):
    """The week's own material first, topped up from the evergreen pool so a
    thin parsha week still fills the page."""
    out, seen = [], set()
    for t in wk["tags"]:
        for s in data["tags"].get(t, []):
            if s not in seen:
                seen.add(s); out.append(s)
    if len(out) < n:
        # rotate the evergreen pool by week so it isn't the same picks forever
        ev = data["evergreen"]
        if ev:
            off = (datetime.date.fromisoformat(wk["w"]).toordinal() // 7) % len(ev)
            for i in range(len(ev)):
                s = ev[(off + i) % len(ev)]
                if s not in seen:
                    seen.add(s); out.append(s)
                if len(out) >= n:
                    break
    return out[:n]

def esc(s):
    return html.escape(str(s or ""), quote=True)

FALLBACK_IMG = "storage/landing/topics.jpg"

def card_html(a, big=False):
    img = a.get("img") or FALLBACK_IMG
    meta = " · ".join(x for x in [a.get("a"), a.get("c"), ("#%s" % a["i"]) if a.get("i") else ""] if x)
    if big:
        return ('<a class="lead" href="articles/{s}.html">'
                '<figure class="lead-shot"><img src="{img}" alt="" loading="eager" fetchpriority="high"></figure>'
                '<div class="lead-txt"><h1>{t}</h1><p class="dek">{d}</p>'
                '<p class="meta">{m}</p></div></a>').format(
            s=esc(a["s"]), img=esc(img), t=esc(a["t"]), d=esc(a.get("d", "")), m=esc(meta))
    return ('<a class="card" href="articles/{s}.html">'
            '<figure><img src="{img}" alt="" loading="lazy"></figure>'
            '<h3>{t}</h3><p class="meta">{m}</p></a>').format(
        s=esc(a["s"]), img=esc(img), t=esc(a["t"]), m=esc(meta))

def render_landing(data):
    wk = week_for(data)
    slugs = pick(data, wk, 7)
    arts = [data["articles"][s] for s in slugs if s in data["articles"]]
    if not arts:
        print("landing: no articles for this week — index.html left alone"); return
    lead, rest = arts[0], arts[1:5]
    ever = [data["articles"][s] for s in data["evergreen"] if s in data["articles"]][:3]
    kicker = " · ".join(x for x in [("Parshas " + wk["p"]) if wk["p"] else "",
                                    ("Shabbos " + wk["hd"]) if wk["hd"] else ""] if x)

    page = LANDING.replace("{{KICKER}}", esc(kicker)) \
                  .replace("{{LEAD}}", card_html(lead, big=True)) \
                  .replace("{{CARDS}}", "".join(card_html(a) for a in rest)) \
                  .replace("{{EVER}}", "".join(card_html(a) for a in ever)) \
                  .replace("{{WEEK}}", esc(wk["w"]))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(page)
    print("index.html: lead '%s' + %d cards + %d evergreen (week %s)"
          % (lead["t"][:44], len(rest), len(ever), wk["w"]))

LANDING = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beis Moshiach — Moshiach, Geula &amp; Chassidus</title>
<meta name="description" content="A weekly reading from the Beis Moshiach archive — chosen for this week's parsha and the Chabad calendar, from 3,541 articles.">
<link rel="canonical" href="https://beismoshiach.org/">
<meta property="og:type" content="website"><meta property="og:site_name" content="beismoshiach.org">
<meta property="og:title" content="Beis Moshiach — Moshiach, Geula &amp; Chassidus">
<meta property="og:description" content="A weekly reading from the archive, chosen for this week's parsha and the Chabad calendar.">
<meta property="og:url" content="https://beismoshiach.org/">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,400&family=Geist:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<style>
  /* Landing — CULTURE/PUBLISHING playbook: one enormous photograph, an
     oversized display voice against small monospaced metadata, generous space,
     motion that narrates rather than decorates. */
  body{background:var(--parchment)}
  .wk{max-width:1240px;margin:0 auto;padding:0 clamp(1.25rem,4vw,3.5rem)}
  .kick{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;
        color:var(--royal);display:flex;align-items:center;gap:.7rem;margin:clamp(2rem,5vw,3.5rem) 0 1.1rem}
  .kick::after{content:"";flex:1;height:1px;background:var(--rule)}
  .lead{display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(1.5rem,4vw,3.2rem);align-items:center;
        padding-bottom:clamp(2rem,5vw,3.5rem);border-bottom:1px solid var(--rule)}
  .lead-shot{margin:0;overflow:hidden;border-radius:3px;background:var(--parchment-deep)}
  .lead-shot img{display:block;width:100%;height:clamp(260px,42vw,520px);object-fit:cover;
        transform:scale(1.04);transition:transform 1.4s var(--ease)}
  .lead:hover .lead-shot img{transform:scale(1)}
  .lead h1{font-family:var(--display);font-weight:900;font-size:clamp(2.1rem,5.4vw,4.2rem);
        line-height:.98;letter-spacing:-.02em;margin:0 0 1rem;color:var(--ink)}
  .lead:hover h1{color:var(--royal)}
  .dek{font-size:1.05rem;line-height:1.6;color:var(--ink-soft);margin:0 0 1.1rem;max-width:46ch}
  .meta{font-family:var(--mono);font-size:.7rem;letter-spacing:.04em;color:var(--royal);margin:0}
  .row{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:clamp(1rem,2.5vw,1.8rem);
       padding-bottom:clamp(2rem,5vw,3.5rem)}
  .card{display:block;color:inherit}
  .card figure{margin:0 0 .8rem;overflow:hidden;border-radius:3px;background:var(--parchment-deep)}
  .card img{display:block;width:100%;height:170px;object-fit:cover;transition:transform .7s var(--ease)}
  .card:hover img{transform:scale(1.05)}
  .card h3{font-family:var(--display);font-weight:600;font-size:1.12rem;line-height:1.25;
        margin:0 0 .4rem;color:var(--ink)}
  .card:hover h3{color:var(--royal)}
  .ways{display:flex;flex-wrap:wrap;gap:.6rem;padding-bottom:clamp(2.5rem,6vw,4rem)}
  .ways a{font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;
        border:1px solid var(--parchment-edge);border-radius:999px;padding:.6rem 1.1rem;color:var(--ink);
        transition:border-color .2s,color .2s,background .2s}
  .ways a:hover{border-color:var(--gold-bright);color:var(--royal);background:var(--parchment-deep)}
  @media(max-width:820px){.lead{grid-template-columns:1fr}.lead-shot{order:-1}}
  /* Motion narrates: sections arrive as you reach them. Native scroll-driven,
     no library; entirely absent when the visitor asks for less motion. */
  @media (prefers-reduced-motion:no-preference){
    @supports (animation-timeline:view()){
      .reveal{animation:rise linear both;animation-timeline:view();animation-range:entry 0% entry 55%}
      @keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
    }
  }
</style></head><body>
<header class="bm-topbar"><div class="bm-inner">
  <a class="bm-wordmark" href="/">beismoshiach<span class="bm-tld">.org</span></a>
  <nav><a href="/topics">Topics</a><a href="/parsha">Parsha</a><a href="/collections">Collections</a>
    <a href="/archives">Archives</a><a href="/search">Search</a><a class="langsw" href="/he/">עברית</a></nav>
</div></header>
<main class="wk" data-week="{{WEEK}}">
  <p class="kick" id="kick">This week · {{KICKER}}</p>
  <div id="lead">{{LEAD}}</div>
  <p class="kick">More for this week</p>
  <div class="row reveal" id="cards">{{CARDS}}</div>
  <p class="kick">From the archive</p>
  <div class="row reveal" id="ever">{{EVER}}</div>
  <p class="kick">Ways in</p>
  <nav class="ways reveal">
    <a href="/collections">Collections</a><a href="/archives">The archive · 3,541 articles</a>
    <a href="/topics">Topics</a><a href="/parsha">By parsha</a><a href="/search">Search</a>
    <a href="https://www.moshiach101.info/" target="_blank" rel="noopener">Moshiach 101 ↗</a>
  </nav>
</main>
<footer class="colophon"><div class="wrap">
  <div class="cf-brand">beismoshiach.org</div>
  A unified archive · 3,541 articles preserved.<br>
  <span style="opacity:.6">Chosen each week for the parsha and the Chabad calendar.</span>
</div></footer>
<script>
/* Keep the page current without a rebuild: the schedule is precomputed, so the
   browser only has to look up the visitor's own week and re-render if it has
   moved on since this HTML was written. */
(function(){
  var main=document.querySelector('.wk'); if(!main) return;
  fetch('assets/weekly.json',{cache:'no-cache'}).then(function(r){return r.json();}).then(function(d){
    var today=new Date().toISOString().slice(0,10);
    var wk=null;
    for(var i=0;i<d.schedule.length;i++){ if(d.schedule[i].w>=today){ wk=d.schedule[i]; break; } }
    if(!wk||wk.w===main.dataset.week) return;               // already current
    var seen={},list=[];
    (wk.tags||[]).forEach(function(t){(d.tags[t]||[]).forEach(function(s){if(!seen[s]){seen[s]=1;list.push(s);}});});
    if(list.length<7&&d.evergreen.length){
      var off=Math.floor(Date.parse(wk.w)/6048e5)%d.evergreen.length;
      for(var j=0;j<d.evergreen.length&&list.length<7;j++){
        var s=d.evergreen[(off+j)%d.evergreen.length]; if(!seen[s]){seen[s]=1;list.push(s);}
      }
    }
    var arts=list.map(function(s){return d.articles[s];}).filter(Boolean);
    if(!arts.length) return;
    var esc=function(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
    var meta=function(a){return [a.a,a.c,a.i?('#'+a.i):''].filter(Boolean).join(' · ');};
    var FB='storage/landing/topics.jpg';
    var card=function(a){return '<a class="card" href="articles/'+esc(a.s)+'.html">'+
      '<figure><img src="'+esc(a.img||FB)+'" alt="" loading="lazy"></figure>'+
      '<h3>'+esc(a.t)+'</h3><p class="meta">'+esc(meta(a))+'</p></a>';};
    var L=arts[0];
    document.getElementById('kick').textContent='This week · '+
      ((wk.p?('Parshas '+wk.p):'')+(wk.p&&wk.hd?' · ':'')+(wk.hd?('Shabbos '+wk.hd):''));
    document.getElementById('lead').innerHTML='<a class="lead" href="articles/'+esc(L.s)+'.html">'+
      '<figure class="lead-shot"><img src="'+esc(L.img||FB)+'" alt=""></figure>'+
      '<div class="lead-txt"><h1>'+esc(L.t)+'</h1><p class="dek">'+esc(L.d||'')+'</p>'+
      '<p class="meta">'+esc(meta(L))+'</p></div></a>';
    document.getElementById('cards').innerHTML=arts.slice(1,5).map(card).join('');
    main.dataset.week=wk.w;
  }).catch(function(){/* the rendered week stands */});
})();
</script>
<script src="https://dreamsitedesign.com/imago-dreamsite.js" defer
        data-domain="DREAMSITEDESIGN.COM"
        data-href="https://dreamsitedesign.com"
        data-perch="DREAMSITEDESIGN.COM"
        data-wing="#FDCB40" data-wing-deep="#8A5B00" data-spot="#0042AF"
        data-paper="#FEF1D0" data-ink="#0A0A0B"></script>
</body></html>"""

if __name__ == "__main__":
    main()
