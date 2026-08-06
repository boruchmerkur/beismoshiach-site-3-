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

PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
JPEG_SOI = bytes([0xFF, 0xD8])
FF = bytes([0xFF])
EOI = bytes([0xD9])

def dims(path):
    """Width/height without a decoder dependency (PNG IHDR + JPEG SOF scan)."""
    import struct
    try:
        with open(path, "rb") as f:
            head = f.read(24)
            if head[:8] == PNG_MAGIC:
                w, h = struct.unpack(">II", head[16:24])
                return w, h
            if head[:2] == JPEG_SOI:
                f.seek(2)
                b = f.read(1)
                while b and b != EOI:
                    while b and b != FF:
                        b = f.read(1)
                    while b == FF:
                        b = f.read(1)
                    if not b:
                        break
                    if 0xC0 <= b[0] <= 0xCF and b[0] not in (0xC4, 0xC8, 0xCC):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    size = struct.unpack(">H", f.read(2))[0]
                    f.read(size - 2)
                    b = f.read(1)
    except Exception:
        pass
    return None

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
    src = clean_img(img.group(1)) if img else None
    wh = dims(os.path.join(ROOT, src.replace("/", os.sep))) if src else None
    return {
        "s": slug,
        "t": title,
        "a": strip(au.group(1)) if au else "",
        "c": strip(dept.group(1)) if dept else "",
        "i": int(iss.group(1)) if iss else None,
        "d": (summ[:190] + "…") if len(summ) > 190 else summ,
        "img": src, "w": (wh or (0, 0))[0], "h": (wh or (0, 0))[1],
    }

def looks_broken(a):
    """Some export titles are body text or the 'Recent Articles' shell."""
    t = a["t"]
    return (t.startswith("Beis Moshiach Magazine") or len(t) > 72 or
            t.lower().startswith(("translated ", "by ")) or not t)

# ------------------------------------------------------------------ tag sources
def from_parsha_page(names=None):
    out = {}
    p = os.path.join(ROOT, "parsha.html")
    if not os.path.isfile(p):
        return out
    t = open(p, encoding="utf-8", errors="replace").read()
    for slug, _name, _n, body in re.findall(
        r'<h2 class="grp" id="([^"]+)">(.*?)<span class="gc">(\d+)</span></h2>\s*<ul class="artlist">(.*?)</ul>',
        t, re.S):
        out.setdefault(slug, [])
        if names is not None:
            names[slug] = strip(_name)
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

# Every tag that is bound to a point in the year. An article carrying one of
# these is only ever shown in its own week.
SEASON_TAGS = set()
for _c in list(OCCASIONS.values()) + list(MONTH_TAGS.values()):
    SEASON_TAGS.update(_c)
SEASON_TAGS.update({"sukkos", "pesach", "chanukah", "purim", "shavuos",
                    "rosh-hashanah", "rosh-hashana", "yom-kippur",
                    "simchas-torah", "lag-baomer", "lag-bomer", "tu-b-shvat",
                    "tisha-b-av", "yud-tes-kislev", "chof-beis-shvat",
                    "yud-shvat", "gimmel-tammuz", "yud-beis-tammuz",
                    "beis-nissan", "yud-alef-nissan", "basi-l-gani",
                    "chai-elul", "elul", "menachem-av", "tishrei", "selichos"})

SMALL = {"of", "the", "and", "b", "l"}

def prettify(slug):
    """menachem-av -> Menachem Av; yud-tes-kislev -> Yud-Tes Kislev."""
    parts = slug.split("-")
    out = []
    for i, w in enumerate(parts):
        out.append(w if (w in SMALL and i) else w.capitalize())
    s = " ".join(out)
    return (s.replace("Yud Tes", "Yud-Tes").replace("Yud Beis", "Yud-Beis")
             .replace("Chof Beis", "Chof-Beis").replace("Yud Alef", "Yud-Alef")
             .replace("Lag Baomer", "Lag BaOmer").replace("Lag Bomer", "Lag BaOmer")
             .replace("Tu B Shvat", "Tu B'Shvat").replace("Tisha B Av", "Tisha B'Av")
             .replace("Basi L Gani", "Basi L'Gani"))

def label_for(tag, labels, parsha_name, parsha_tag):
    """What to tell the reader about why this is here."""
    if tag == parsha_tag and parsha_name:
        return "Parshas " + parsha_name
    nm = labels.get(tag)
    if nm:
        return nm
    return prettify(tag)

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

    LABELS = {}
    tagmap = from_parsha_page(LABELS)
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
                      "ptag": tags[0] if (pname and tags) else "",
                      "labels": {t: label_for(t, LABELS, pname, tags[0] if (pname and tags) else "")
                                 for t in tags},
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
    # which date-bound tags each article carries, so nothing shows out of season
    season = {}
    for t, slugs in keep.items():
        if t in SEASON_TAGS:
            for s in slugs:
                season.setdefault(s, []).append(t)
    def have(f):
        return os.path.isfile(os.path.join(ROOT, "storage", "art", f))
    artmap = {
        "season": {t: "storage/art/" + f for t, f in SEASON_ART.items() if have(f)},
        "dept": {d: "storage/art/" + f for d, f in DEPT_ART.items() if have(f)},
    }
    data = {"built": today.isoformat(), "articles": arts, "tags": keep,
            "evergreen": ever, "season": season, "art": artmap, "schedule": sched}
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
    thin parsha week still fills the page.

    The top-ups are filtered by season: a piece tagged Sukkos has no business
    on the page in Av. Anything carrying a date tag other than this week's own
    is held back until its time comes round."""
    season = data.get("season", {})
    here = set(wk["tags"])

    def in_season(s):
        tags = set(season.get(s, []))
        return (not tags) or bool(tags & here)

    out, seen, why = [], set(), {}
    for t in wk["tags"]:
        for s in data["tags"].get(t, []):
            # a piece can sit under this week's parsha and still be a Sukkos
            # piece; the date tag wins either way
            if s not in seen and in_season(s):
                seen.add(s); out.append(s); why[s] = t
    if len(out) < n:
        ev = data["evergreen"]
        if ev:
            # rotate the pool by week so it isn't the same picks forever
            off = (datetime.date.fromisoformat(wk["w"]).toordinal() // 7) % len(ev)
            for i in range(len(ev)):
                s = ev[(off + i) % len(ev)]
                if s in seen:
                    continue
                if not in_season(s):
                    continue          # out of season — wait for its week
                seen.add(s); out.append(s)
                if len(out) >= n:
                    break
    pick.why = why
    return out[:n]

def esc(s):
    return html.escape(str(s or ""), quote=True)

FALLBACK_IMG = "storage/landing/topics.jpg"
# Curated stand-ins for a week whose own pictures will not carry a hero.
HEROES = ["storage/landing/topics.jpg", "storage/landing/archive.jpg",
          "storage/landing/parsha.jpg", "storage/landing/dvar-malchus.jpg",
          "storage/landing/moshiach-geula.jpg"]

# Commissioned editorial art, keyed by department and by season. Drop a file
# into storage/art/ and it is used automatically the next time this runs; until
# then the card is set as type. Deliberately no likenesses — the Rebbe's own
# photographs are used for that, and are not something to generate.
DEPT_ART = {
    "D'var Malchus": "sichah.jpg", "Moshiach & Geula": "geula.jpg",
    "Moshiach & Hakhel": "geula.jpg", "Parsha Thought": "parsha.jpg",
    "Chabad History": "history.jpg", "Memoirs": "memoirs.jpg",
    "Diary": "memoirs.jpg", "Halacha 2 Go": "halacha.jpg",
    "Miracle Story": "miracle.jpg", "Chinuch": "chinuch.jpg",
    "Editorial": "editorial.jpg", "Ha'yom Yom & Moshiach": "hayomyom.jpg",
    "Feature": "feature.jpg", "Profile": "feature.jpg", "Interview": "feature.jpg",
    "Shlichus Stories": "shlichus.jpg", "Tzivos Hashem": "chinuch.jpg",
}
SEASON_ART = {
    "elul": "elul.jpg", "menachem-av": "av.jpg", "tishrei": "tishrei.jpg",
    "rosh-hashanah": "tishrei.jpg", "rosh-hashana": "tishrei.jpg",
    "yom-kippur": "tishrei.jpg", "sukkos": "sukkos.jpg",
    "simchas-torah": "sukkos.jpg", "chanukah": "chanukah.jpg",
    "purim": "purim.jpg", "pesach": "pesach.jpg", "shavuos": "shavuos.jpg",
    "lag-baomer": "lagbaomer.jpg", "lag-bomer": "lagbaomer.jpg",
    "tisha-b-av": "av.jpg", "yud-shvat": "yudshvat.jpg",
    "basi-l-gani": "yudshvat.jpg", "yud-tes-kislev": "kislev.jpg",
}

def art_for(a, season_tags=()):
    """Commissioned images for this piece, best first: the season's own art,
    then the department's. Returns every candidate so a card whose first
    choice is already on the page can fall back to its second rather than
    dropping to type."""
    out = []
    for t in season_tags:
        f = SEASON_ART.get(t)
        if f and os.path.isfile(os.path.join(ROOT, "storage", "art", f)):
            p = "storage/art/" + f
            if p not in out:
                out.append(p)
    f = DEPT_ART.get((a.get("c") or "").strip())
    if f and os.path.isfile(os.path.join(ROOT, "storage", "art", f)):
        p = "storage/art/" + f
        if p not in out:
            out.append(p)
    return out

def is_art(a):
    """Worth showing as a picture. Author headshots live in category-pics and
    are bylines, not editorial images — two different portraits of the same
    columnist on one page looks like a mistake, because it is one."""
    img = a.get("img")
    return (bool(img) and "category-pics" not in img
            and a.get("w", 0) >= 430 and a["w"] / max(a.get("h", 1), 1) >= 1.15)

def card_html(a, big=False, used=None):
    used = used if used is not None else set()
    meta = " · ".join(x for x in [a.get("a"), a.get("c"), ("#%s" % a["i"]) if a.get("i") else ""] if x)
    # say plainly what makes this timely, rather than only the department
    # the timeliness reason if there is one, else the department it ran in,
    # so every card says what it is
    why = a.get("_why") or ""
    chip = why or a.get("c") or "From the archive"
    tag = '<span class="why%s">%s</span>' % ("" if why else " plain", esc(chip))
    if big:
        img = a.get("img") or FALLBACK_IMG
        used.add(img)
        return ('<a class="lead" href="articles/{s}.html">'
                '<figure class="lead-shot"><img src="{img}" alt="" loading="eager" fetchpriority="high"></figure>'
                '<div class="lead-txt">{why}<h1>{t}</h1><p class="dek">{d}</p>'
                '<p class="meta">{m}</p></div></a>').format(
            s=esc(a["s"]), img=esc(img), t=esc(a["t"]), d=esc(a.get("d", "")),
            m=esc(meta), why=tag)
    # a picture only if it is a real one, and only once per page
    if is_art(a) and a["img"] not in used:
        used.add(a["img"])
        return ('<a class="card" href="articles/{s}.html">'
                '<figure><img src="{img}" alt="" loading="lazy"></figure>'
                '{why}<h3>{t}</h3><p class="meta">{m}</p></a>').format(
            s=esc(a["s"]), img=esc(a["img"]), t=esc(a["t"]), m=esc(meta), why=tag)
    # a commissioned image for the season/department, if one exists yet
    for art in art_for(a, a.get("_season", ())):
        if art in used:
            continue
        used.add(art)
        return ('<a class="card" href="articles/{s}.html">'
                '<figure><img src="{img}" alt="" loading="lazy"></figure>'
                '{why}<h3>{t}</h3><p class="meta">{m}</p></a>').format(
            s=esc(a["s"]), img=esc(art), t=esc(a["t"]), m=esc(meta), why=tag)
    # otherwise let the type carry it
    dept = esc(why or a.get("c") or "From the archive")
    return ('<a class="card txt" href="articles/{s}.html">'
            '<span class="dept">{dept}</span><h3>{t}</h3><p class="meta">{m}</p></a>').format(
        s=esc(a["s"]), dept=dept, t=esc(a["t"]), m=esc(meta))

def render_landing(data):
    wk = week_for(data)
    slugs = pick(data, wk, 7)
    arts = [data["articles"][s] for s in slugs if s in data["articles"]]
    if not arts:
        print("landing: no articles for this week — index.html left alone"); return
    # Lead on the week's strongest picture. Over half the archive's images are
    # author headshots from category-pics — fine at card size, weak blown up to
    # a hero. Everything in `arts` is already this week's material, so choosing
    # among them on image strength costs nothing in relevance.
    def is_photo(a):
        """Good enough to blow up: a real width and a landscape-ish crop.
        Headshots are small and tall, and they fall out on the numbers rather
        than on a guess about the filename."""
        return (bool(a.get("img")) and a.get("w", 0) >= 430
                and a["w"] / max(a.get("h", 1), 1) >= 1.15)
    order = ([a for a in arts if is_photo(a)] +
             [a for a in arts if not is_photo(a)])
    lead = order[0]
    rest = [a for a in arts if a["s"] != lead["s"]][:4]
    if not is_photo(lead):
        commissioned = art_for(lead, wk["tags"])
        if commissioned:
            lead = dict(lead, img=commissioned[0])
        else:
            wkno = datetime.date.fromisoformat(wk["w"]).toordinal() // 7
            lead = dict(lead, img=HEROES[wkno % len(HEROES)])
    # The archive row runs through the same season gate as everything else —
    # it is where the Sukkos piece was turning up in Av — and never repeats
    # something already on the page.
    shown = {lead["s"]} | {a["s"] for a in rest}
    season, here = data.get("season", {}), set(wk["tags"])
    ever = []
    for s in data["evergreen"]:
        if s in shown or s not in data["articles"]:
            continue
        tags = set(season.get(s, []))
        if tags and not (tags & here):
            continue
        ever.append(data["articles"][s])
        if len(ever) == 3:
            break
    kicker = " · ".join(x for x in [("Parshas " + wk["p"]) if wk["p"] else "",
                                    ("Shabbos " + wk["hd"]) if wk["hd"] else ""] if x)

    # Tell the reader why each piece is here this week — "Parshas Re'eh",
    # "Menachem Av" — rather than only naming the department it ran in.
    labels = wk.get("labels", {})
    whyof = getattr(pick, "why", {}) or {}
    def dress(a):
        return dict(a, _season=wk["tags"], _why=labels.get(whyof.get(a["s"], ""), ""))

    used = set()
    page = LANDING.replace("{{KICKER}}", esc(kicker)) \
                  .replace("{{LEAD}}", card_html(dress(lead), big=True, used=used)) \
                  .replace("{{CARDS}}", "".join(card_html(dress(a), used=used) for a in rest)) \
                  .replace("{{EVER}}", "".join(card_html(dress(a), used=used) for a in ever)) \
                  .replace("{{WEEK}}", esc(wk["w"]))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(page)
    print("index.html: lead '%s' + %d cards + %d evergreen (week %s)"
          % (lead["t"][:44], len(rest), len(ever), wk["w"]))

LANDING = r"""<!DOCTYPE html><html lang="en"><head>
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
  /* Photographs of the Rebbe are never cropped to fit a box. The art is 3:2
     and the archive photos are close to it, so heights stay even anyway. */
  .lead-shot img{display:block;width:100%;height:auto;
        transform:scale(1.02);transition:transform 1.4s var(--ease)}
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
  .card img{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:contain;
        background:var(--parchment-deep);transition:transform .7s var(--ease)}
  .card:hover img{transform:scale(1.05)}
  .card h3{font-family:var(--display);font-weight:600;font-size:1.12rem;line-height:1.25;
        margin:0 0 .4rem;color:var(--ink)}
  .card:hover h3{color:var(--royal)}
  /* No picture worth printing? Let the type carry it — a set-in card rather
     than a columnist's headshot stretched into a photograph. */
  .card.txt{display:flex;flex-direction:column;justify-content:center;min-height:0;aspect-ratio:3/2;
        padding:1.1rem 1.2rem;background:var(--parchment-deep);border:1px solid var(--parchment-edge);
        border-left:3px solid var(--gold-bright);border-radius:3px;
        transition:border-color .2s,transform .3s var(--ease)}
  .card.txt:hover{transform:translateY(-2px);border-color:var(--royal);border-left-color:var(--royal)}
  .card.txt .dept{font-family:var(--mono);font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;
        color:var(--royal);margin-bottom:.5rem}
  .card.txt h3{font-size:1.3rem}
  /* Why this piece is here this week — the parsha or the date it belongs to. */
  .why{display:inline-block;font-family:var(--mono);font-size:.58rem;letter-spacing:.1em;
        text-transform:uppercase;color:var(--royal);background:var(--royal-soft);
        border-radius:2px;padding:.28rem .5rem;margin:0 0 .5rem}
  .lead-txt .why{font-size:.64rem;margin-bottom:.9rem}
  .why.plain{color:var(--ink-soft);background:transparent;padding-left:0}
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
    <a id="installapp" href="#" hidden>Install the app</a>
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
    var seen={},list=[],here={};
    (wk.tags||[]).forEach(function(t){here[t]=1;});
    var inSeason=function(s){var st=(d.season||{})[s]||[];
      return !st.length||st.some(function(x){return here[x];});};
    var why={};
    (wk.tags||[]).forEach(function(t){(d.tags[t]||[]).forEach(function(s){
      if(!seen[s]&&inSeason(s)){seen[s]=1;list.push(s);why[s]=t;}});});
    if(list.length<7&&d.evergreen.length){
      var off=Math.floor(Date.parse(wk.w)/6048e5)%d.evergreen.length;
      for(var j=0;j<d.evergreen.length&&list.length<7;j++){
        var s=d.evergreen[(off+j)%d.evergreen.length];
        if(seen[s]) continue;
        if(!inSeason(s)) continue;               /* out of season? wait its turn */
        seen[s]=1;list.push(s);
      }
    }
    var arts=list.map(function(s){var a=d.articles[s];
      return a?Object.assign({},a,{_why:why[s]||''}):null;}).filter(Boolean);
    if(!arts.length) return;
    var esc=function(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
    var meta=function(a){return [a.a,a.c,a.i?('#'+a.i):''].filter(Boolean).join(' · ');};
    var FB='storage/landing/topics.jpg';
    var used={};
    var art=function(a){return a.img&&a.img.indexOf('category-pics')<0&&a.w>=430&&a.w/Math.max(a.h,1)>=1.15;};
    var AM=d.art||{season:{},dept:{}};
    var LB=wk.labels||{};
    var whyOf=function(a){return LB[a._why||'']||'';};
    var chip=function(a){var w=whyOf(a);
      return '<span class="why'+(w?'':' plain')+'">'+esc(w||a.c||'From the archive')+'</span>';};
    var picCard=function(a,src){ used[src]=1;
      return '<a class="card" href="articles/'+esc(a.s)+'.html">'+
        '<figure><img src="'+esc(src)+'" alt="" loading="lazy"></figure>'+
        chip(a)+'<h3>'+esc(a.t)+'</h3><p class="meta">'+esc(meta(a))+'</p></a>';};
    var artFor=function(a){                       /* season art first, then dept */
      var o=[];
      (wk.tags||[]).forEach(function(t){var f=AM.season[t]; if(f&&o.indexOf(f)<0)o.push(f);});
      var g=AM.dept[(a.c||'').trim()]; if(g&&o.indexOf(g)<0)o.push(g);
      return o;};
    var card=function(a){
      if(art(a)&&!used[a.img]) return picCard(a,a.img);
      var cand=artFor(a);
      for(var i=0;i<cand.length;i++){ if(!used[cand[i]]) return picCard(a,cand[i]); }
      return '<a class="card txt" href="articles/'+esc(a.s)+'.html">'+
        '<span class="dept">'+esc(whyOf(a)||a.c||'From the archive')+'</span>'+
        '<h3>'+esc(a.t)+'</h3><p class="meta">'+esc(meta(a))+'</p></a>';};
    /* lead on the strongest picture — headshots read poorly at hero size */
    var photo=function(a){return a.img&&a.img.indexOf('category-pics')<0&&a.w>=430&&a.w/Math.max(a.h,1)>=1.15;};
    var HEROES=['storage/landing/topics.jpg','storage/landing/archive.jpg','storage/landing/parsha.jpg','storage/landing/dvar-malchus.jpg','storage/landing/moshiach-geula.jpg'];
    var L=arts.filter(photo)[0];
    if(L) used[L.img]=1;
    if(!L){L=Object.assign({},arts[0]);
      var AM0=d.art||{season:{},dept:{}},hero=null;
      (wk.tags||[]).forEach(function(t){if(!hero&&AM0.season[t])hero=AM0.season[t];});
      if(!hero)hero=AM0.dept[(L.c||'').trim()];
      L.img=hero||HEROES[Math.floor(Date.parse(wk.w)/6048e5)%HEROES.length];}
    arts=[L].concat(arts.filter(function(a){return a.s!==L.s;}));
    document.getElementById('kick').textContent='This week · '+
      ((wk.p?('Parshas '+wk.p):'')+(wk.p&&wk.hd?' · ':'')+(wk.hd?('Shabbos '+wk.hd):''));
    document.getElementById('lead').innerHTML='<a class="lead" href="articles/'+esc(L.s)+'.html">'+
      '<figure class="lead-shot"><img src="'+esc(L.img||FB)+'" alt=""></figure>'+
      '<div class="lead-txt">'+chip(L)+'<h1>'+esc(L.t)+'</h1><p class="dek">'+esc(L.d||'')+'</p>'+
      '<p class="meta">'+esc(meta(L))+'</p></div></a>';
    document.getElementById('cards').innerHTML=arts.slice(1,5).map(card).join('');
    main.dataset.week=wk.w;
  }).catch(function(){/* the rendered week stands */});
})();
</script>
<script>
/* Offer the app where the other ways in are listed. The link only appears
   when the browser says the site is actually installable. */
(function(){
  var a=document.getElementById('installapp'); if(!a) return;
  var deferred=null;
  addEventListener('beforeinstallprompt',function(e){
    e.preventDefault(); deferred=e; a.hidden=false;
  });
  a.addEventListener('click',function(e){
    e.preventDefault();
    if(!deferred) return;
    deferred.prompt();
    deferred.userChoice.then(function(){ deferred=null; a.hidden=true; });
  });
  addEventListener('appinstalled',function(){ a.hidden=true; });
  // already running as an installed app? then there is nothing to offer
  if(matchMedia('(display-mode: standalone)').matches) a.hidden=true;
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
