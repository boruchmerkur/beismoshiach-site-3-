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

def tidy(s):
    """Collapse whitespace, and close up the gaps our own tag-stripping opens.

    The export wraps fragments in spans — <span>MH</span>”M — so replacing a
    tag with a space invents one that was never in the text. This puts back
    only what we displaced; no character of the writing is changed."""
    s = re.sub(r"\s+", " ", s or "").strip()
    s = re.sub(r" +([’'”\"),.;:!?״׳])", r"\1", s)
    s = re.sub(r"([(“]) +", r"\1", s)
    # a drop cap is set in its own tag — <strong>R</strong>abbi — so stripping
    # the tag leaves "R abbi". Put the initial back on its word. Never for A or
    # I: they are words in their own right, and "A family" must stay two.
    s = re.sub(r"^([B-HJ-Z]) (?=[a-z]{2})", r"\1", s)
    return s

# lines that are apparatus, not writing: credits, separators, captions
SKIP_P = re.compile(
    r"(?i)^\s*(\*+\s*$|\[|\(photo|photos? by|translated (and|by)|reprinted|"
    r"presented by|by [A-Z][a-z]+ [A-Z]|article originally|"
    r"for more information|to subscribe|continued (on|from))")

def cut(s, n):
    """Trim to a length the layout can hold, on a sentence if one lands near
    the end, otherwise on a word. The text itself is never altered."""
    s = tidy(s)
    if len(s) <= n:
        return s
    head = s[:n]
    stop = max(head.rfind(". "), head.rfind("? "), head.rfind("! "))
    if stop >= n * 0.55:                     # a whole sentence, cleanly
        return head[:stop + 1]
    return head[:head.rfind(" ")].rstrip(" ,;:—-") + "…"

# the dek convention is clause * clause; a clause that only credits a source is
# apparatus — it belongs on the article, not on a card. It sits at either end.
CRED = (r"(from (chapter|the )|translated |presented by|adapted |part \w+ of|"
        r"excerpt|reprinted|source[sd]?\b|based on|by [A-Z])")
CREDIT_END = re.compile(r"(?i)\s*\*\s*" + CRED + r"[^*]*$")
CREDIT_START = re.compile(r"(?i)^" + CRED + r"[^*]*?(\*\s*|(?<=[.)])\s+(?=[A-Z0-9“]))")
# a caption travels inside the paragraph it illustrates; it is not the writing
CAPTION = re.compile(r'(?is)<span class="thumbnail-caption".*?</span>')
# a dek that opens like this is a quote lifted from the middle of the argument:
# true to the piece, but it cannot introduce it
MIDWAY = re.compile(r"(?i)^(this|that|these|those|it|he|she|they|such|so|also|"
                    r"thus|therefore|hence|but|however|and|yet|in addition|"
                    r"furthermore|moreover|the above|as (a result|mentioned))\b")

def lede(t):
    """The magazine's own dek if it wrote one, plus the opening of the piece.

    Both are lifted verbatim — the point is to show the writing, so nothing is
    summarised, rewritten or generated."""
    pull = re.search(r'<p class="entry-pull">(.*?)</p>', t, re.S)
    dek = tidy(strip(pull.group(1))) if pull else ""
    dek = CREDIT_START.sub("", CREDIT_END.sub("", dek)).strip()
    if re.match(r"(?i)^" + CRED, dek):       # nothing but the credit line
        dek = ""
    # the export dropped some drop-cap initials, leaving the dek headless
    # ("s the new school year begins…") — a fragment can't introduce anything
    if dek and not (dek[0].isupper() or dek[0].isdigit() or dek[0] in "“\"‘'"):
        dek = ""
    body = re.search(r'<div class="entry-body">(.*)', t, re.S)
    first = ""
    if body:
        for p in re.findall(r"<p[^>]*>(.*?)</p>", CAPTION.sub("", body.group(1)), re.S):
            p = tidy(strip(p))
            if len(p) < 60 or SKIP_P.match(p):
                continue
            if not (p[0].isupper() or p[0].isdigit() or p[0] in "“\"‘'"):
                continue                     # another headless drop cap
            first = p
            break
    if not dek:                              # no dek written — open with the piece
        return cut(first, 340), ""
    if first[:40] and dek[:40] and first[:40] == dek[:40]:
        return cut(dek, 340), ""             # the dek is the opening; don't repeat it
    if MIDWAY.match(dek) and first:
        return cut(first, 300), cut(dek, 300)   # let the piece open itself
    return cut(dek, 300), cut(first, 300)

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
    img = re.search(r'<div class="entry-body">.*?<img[^>]+src="([^"]+)"', t, re.S)
    dek, open_ = lede(t)
    src = clean_img(img.group(1)) if img else None
    wh = dims(os.path.join(ROOT, src.replace("/", os.sep))) if src else None
    # Is the heading a line of the article's own prose? Decided here, where the
    # body is open, rather than guessed at later from the title's shape. A long
    # heading that appears verbatim inside the text was lifted from it — that is
    # what happened to "The voting public must now remind the prime minister
    # that he received", whose real title survives in its slug. Short headings
    # are exempt: a title legitimately recurs in its own opening line.
    # Only text found DEEP in the piece counts. Plenty of articles repeat their
    # own title as the first line of the body, and reading that as evidence of
    # theft threw 144 sound articles out of the index. A title is not lifted
    # because it appears at the top; it is lifted when it turns up in the
    # middle of a paragraph six hundred characters down.
    # Narrowed to the actual signature of the fault: a long heading that stops
    # without punctuation AND is found in the middle of the piece. Testing only
    # "appears in the body" cost 143 sound articles, because a title recurring
    # in its own prose is ordinary writing, not evidence of anything.
    lifted = 0
    if (len(title) > 55
            and not title.rstrip().endswith(("?", "!", ".", "”", "’", '"', "'"))
            and not agrees_with_slug(slug, title)):
        body = re.search(r'<div class="entry-body">(.*)', t, re.S)
        if body and _norm(strip(body.group(1))).find(_norm(title)[:60]) > 200:
            lifted = 1
    return {
        "s": slug,
        "t": title,
        "a": strip(au.group(1)) if au else "",
        "c": strip(dept.group(1)) if dept else "",
        "i": int(iss.group(1)) if iss else None,
        "d": dek, "x": open_, "lift": lifted,
        "img": src, "w": (wh or (0, 0))[0], "h": (wh or (0, 0))[1],
    }

def looks_broken(a):
    """Some export titles are body text or the 'Recent Articles' shell; a few
    entries are an embedded video with no prose, which has nothing to show on
    a card.

    The 'len > 72' that used to be here was the same mistake as the old
    headline test, made twice: it dropped real headlines from the index before
    anything downstream could even consider them. The one test now lives in
    reads_as_headline, which checks whether the heading is the article's own
    opening rather than guessing from its length.
    """
    t = a["t"]
    return (not t or not reads_as_headline(a) or
            not (a.get("d") or a.get("x")))

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

    # ---- Moshiach & Science, from tools/build_science.py
    # The department has no tag page, so from_tag_pages() never sees it and the
    # pools list below would look for a key that does not exist. science.json is
    # the department's index; register it here as a tag like any other, and the
    # 28 pieces become eligible for the evergreen row and for /science/ alike.
    sci = os.path.join(ROOT, "assets", "science.json")
    if os.path.isfile(sci):
        with open(sci, encoding="utf-8") as f:
            rows = json.load(f).get("items", [])
        slugs = [r["s"] for r in rows if r.get("why") == "department"]
        tagmap["moshiach-science"] = slugs
        LABELS.setdefault("moshiach-science", "Moshiach & Science")
        print("moshiach-science: %d slugs registered as a tag" % len(slugs))
    else:
        print("moshiach-science: assets/science.json missing — run tools/build_science.py")

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
    # moshiach-science is in this list so the department reaches the landing on
    # its own, in the same card as everything else. It is a round robin, so a
    # 28-article department takes one slot per pass and never crowds the row.
    # The whole department also has its own page at /science/, where each piece
    # sits beside the live wire.
    pools = [tagmap.get(t, [])[:12] for t in
             ["moshiach-geula", "shleimus-ha-aretz", "chai-vkayam", "miracle-story",
              "beis-hamikdash", "chinuch", "igrot-kodesh", "rebbe", "moshiach-science"]]
    ever = []
    for i in range(12):                      # round robin, so no single column
        for pool in pools:                   # can monopolise the top of the pool
            if i < len(pool) and pool[i] not in ever:
                ever.append(pool[i])
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
    weekpicks = []
    # Take one from each of the week's tags in turn rather than emptying the
    # first. Ki Seitzei has more than seven pieces to itself, so a straight
    # walk gave the whole page one chip repeated seven times and Elul — which
    # is the half of the date most readers are actually living in — never
    # appeared at all. The parsha still leads each cycle, so it stays the
    # larger share.
    # A piece can sit under this week's parsha and still be a Sukkos piece;
    # the date tag wins either way.
    lists = [[s for s in data["tags"].get(t, []) if in_season(s)] for t in wk["tags"]]
    for i in range(max((len(L) for L in lists), default=0)):
        for t, L in zip(wk["tags"], lists):
            if i < len(L) and L[i] not in seen:
                seen.add(L[i]); weekpicks.append(L[i]); why[L[i]] = t

    # A standing place for the strands that do not expire. The parsha turns
    # over every week; the magazine's argument about the Land, and its own
    # editorial voice, are current in any week — and a page that is only parsha
    # reads like a bulletin rather than a magazine. Rotated by week, so it is a
    # different piece each time instead of the same one forever.
    wknum = datetime.date.fromisoformat(wk["w"]).toordinal() // 7
    standing = []
    for t in STANDING:
        # Reject the broken headings here rather than downstream. Four of the
        # fourteen shleimus ha'aretz pieces open with a line of body text as
        # their <h1>, and if one of those wins the rotation the filter further
        # down drops it and the strand simply vanishes for that week — the slot
        # would be silently empty in exactly the weeks it was wanted.
        pool = [s for s in data["tags"].get(t, [])
                if s not in seen and in_season(s)
                and reads_as_headline(data["articles"].get(s, {}))]
        if pool:
            s = pool[wknum % len(pool)]
            seen.add(s); standing.append(s); why[s] = t

    # Interleaved rather than appended: the parsha alone can fill all seven
    # slots, and anything added after that never survives the cut.
    out = (weekpicks[:2] + standing[:1] + weekpicks[2:4]
           + standing[1:] + weekpicks[4:])
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

# ------------------------------------------------------------------- featured
# One hand-picked piece, held under the lead until it is changed here. The rest
# of the page re-picks itself every week from the archive; this does not, which
# is the point of it — it is the editor's slot.
#
# It sits in its own element, so the script that re-renders the page for the
# visitor's own week leaves it alone: that script rewrites #lead and #cards and
# nothing else.
#
# Set FEATURE = None to take it down.
FEATURE = {
    "href": "https://rebbesletters.com/hadran%20alach.dc",
    "kicker": "Featured",
    "title": "Hadran Alach, Igros Kodesh",
    "dek": "One shliach in Toronto has just made a siyum on the whole of the "
           "Igros Kodesh — 42 volumes, more than fifteen thousand letters, at "
           "ten pages a day, held for some thirty years.",
    "img": "storage/featured/deitsch-kos-shel-bracha.jpg",
    "meta": "Avrohom Reinitz · Beis Moshiach #1515 · on rebbesletters.com",
}

# Strands that never go out of date, given a standing place on the page beside
# whatever the parsha happens to be. The chip says which strand it is, so a
# reader can see why a piece about the Land is sitting under Ki Savo.
STANDING = {
    "shleimus-ha-aretz": "Shleimus HaAretz",
    "editorial": "Editorial",
}

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
    """Commissioned images for this piece, best first.

    The piece's OWN reason comes first: a Shoftim piece must not be illustrated
    with the Elul wheat while its badge reads "Parshas Shoftim". Only then the
    week's other season art, then the department's. Every candidate is returned
    so a card whose first choice is taken falls back rather than dropping to type."""
    out = []
    def add(f):
        if f and os.path.isfile(os.path.join(ROOT, "storage", "art", f)):
            q = "storage/art/" + f
            if q not in out:
                out.append(q)
    own = a.get("_whytag")
    add(SEASON_ART.get(own))                      # the date this piece is here for
    add(DEPT_ART.get((a.get("c") or "").strip())) # else what the piece is
    # deliberately NOT another date's art: a piece badged "Parshas Shoftim"
    # illustrated with the Elul wheat contradicts its own label. A neutral
    # photograph is a better fallback than a wrong one.
    return out

def is_art(a):
    """A real photograph from the article itself — always preferred over
    commissioned art, which is only ever a stand-in. Author headshots from
    category-pics stay out: two portraits of the same columnist on one page
    reads as a mistake, because it is one."""
    img = a.get("img")
    return bool(img) and "category-pics" not in img and a.get("w", 0) >= 400

def is_byline(a):
    img = a.get("img")
    return bool(img) and "category-pics" in img

def portrait_class(a):
    """Tall pictures need the crop anchored high or the subject loses his head."""
    w, h = a.get("w", 0), a.get("h", 1) or 1
    return " class=\"port\"" if w and w / h < 1.15 else ""

def blurb(a, txt=False):
    """The magazine's own words — its dek, and on a type card the opening of
    the piece as well. Verbatim; nothing here is written for it.

    The one liberty is the separator: Beis Moshiach divides the clauses of a
    dek with an asterisk, which on screen reads as a stray mark. It is set as
    a middot instead — the same break, in the glyph the web uses for it."""
    s = a.get("d") or a.get("x") or ""
    # a type card has room for both; so does a card whose dek is a bare line
    if a.get("d") and a.get("x") and (txt or len(a["d"]) < 110):
        s = a["d"] + " * " + a["x"]   # set as a middot below
    if not s:
        return ""
    return '<p class="blurb">%s</p>' % re.sub(r" \*+ ", " · ", esc(s))

def feature_html():
    """The editor's slot. Empty markup when FEATURE is None, so taking it down
    leaves no heading standing over nothing."""
    f = FEATURE
    if not f:
        return ""
    off = "://" in f["href"]
    return (
        '\n  <p class="kick">{k}</p>\n'
        '  <a class="feature reveal" href="{h}"{t}>\n'
        '    <figure><img src="{i}" alt="" loading="lazy"></figure>\n'
        '    <div class="feat-txt"><h2>{ti}</h2><p class="dek">{d}</p>'
        '<p class="meta">{m}</p></div>\n'
        '  </a>\n'
    ).format(
        k=esc(f.get("kicker", "Featured")), h=esc(f["href"]),
        t=' target="_blank" rel="noopener"' if off else "",
        i=esc(f["img"]), ti=esc(f["title"]), d=esc(f.get("dek", "")),
        m=esc(f.get("meta", "")))

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
                '<div class="lead-txt">{why}<h1>{t}</h1><p class="dek">{d}</p>{x}'
                '<p class="meta">{m}</p></div></a>').format(
            s=esc(a["s"]), img=esc(img), t=esc(a["t"]), d=re.sub(r" \*+ ", " · ", esc(a.get("d", ""))),
            m=esc(meta), why=tag,
            x=('<p class="open">%s</p>' % esc(a["x"])) if a.get("x") else "")
    # a picture only if it is a real one, and only once per page
    if is_art(a) and a["img"] not in used:
        used.add(a["img"])
        return ('<a class="card" href="articles/{s}.html">'
                '<figure><img src="{img}"{pc} alt="" loading="lazy"></figure>'
                '{why}<h3>{t}</h3>{b}<p class="meta">{m}</p></a>').format(
            s=esc(a["s"]), img=esc(a["img"]), t=esc(a["t"]), m=esc(meta), why=tag,
            pc=portrait_class(a), b=blurb(a))
    # the writer's own byline portrait — the article's real picture, but only
    # one to a page
    if is_byline(a) and a["img"] not in used and not any("category-pics" in u for u in used):
        used.add(a["img"])
        return ('<a class="card" href="articles/{s}.html">'
                '<figure><img src="{img}"{pc} alt="" loading="lazy"></figure>'
                '{why}<h3>{t}</h3>{b}<p class="meta">{m}</p></a>').format(
            s=esc(a["s"]), img=esc(a["img"]), t=esc(a["t"]), m=esc(meta), why=tag,
            pc=portrait_class(a), b=blurb(a))
    # a commissioned image for the season/department, if one exists yet
    for art in art_for(a, a.get("_season", ())):
        if art in used:
            continue
        used.add(art)
        return ('<a class="card" href="articles/{s}.html">'
                '<figure><img src="{img}" alt="" loading="lazy"></figure>'
                '{why}<h3>{t}</h3>{b}<p class="meta">{m}</p></a>').format(
            s=esc(a["s"]), img=esc(art), t=esc(a["t"]), m=esc(meta), why=tag, b=blurb(a))
    # otherwise let the type carry it
    return ('<a class="card txt" href="articles/{s}.html">'
            '{why}<h3>{t}</h3>{b}<p class="meta">{m}</p></a>').format(
        s=esc(a["s"]), why=tag, t=esc(a["t"]), m=esc(meta), b=blurb(a, txt=True))

APPARATUS = re.compile(r"(?i)^(beis moshiach magazine|translated\b|presented by|"
                       r"adapted from\b|reprinted\b|photos? by|bs\W{0,2}d\b|dear reader|"
                       r"prepared for publication)")

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

_STOPW = set("a an the of to in on for and or is it as at by be with that this from".split())

def agrees_with_slug(slug, title):
    """The slug was made from the real title, so it is an independent record of
    it. When the two share vocabulary the heading is the title, whatever else
    it does — recur in its own prose, run long, end on a preposition. When they
    share nothing, the heading came from somewhere else."""
    sw = [w for w in _norm(slug).split() if len(w) > 2 and w not in _STOPW]
    tw = set(_norm(title).split())
    if len(sw) < 3:
        return True                       # too short to judge; assume honest
    hit = sum(1 for w in sw if w in tw or any(x.startswith(w[:5]) for x in tw))
    return hit / len(sw) >= 0.45

def reads_as_headline(a):
    """Is this <h1> a title, or a line of the article's own body?

    The old test guessed from shape — short, or a question — and threw out 415
    articles for the crime of having an ordinary magazine headline: "22 Years
    Have Come and Gone and the Silence Is Deafening", "A Beacon of Light in the
    Darkness of Soviet Russia". Over 45 characters and over 8 words is most
    real headlines, so the landing was drawing from a fraction of the archive
    and half the shleimus ha'aretz writing was unreachable.

    This checks evidence instead. If the heading is how the piece OPENS, it is
    not a title, it is the first sentence — and that is a fact about the file,
    not a hunch about the prose. Length, word count and what the last word
    happens to be are none of our business: "Reaching out to Israelis in the
    Land Down Under" is a headline, and so is "Firebrand"."""
    ti = (a.get("t") or "").strip()
    if not ti:
        return False
    if ti[0].islower():                      # "goes out" — cut mid-sentence
        return False
    if APPARATUS.match(ti):                  # export shell, credit line, preamble
        return False
    if len(ti) > 95:                         # a paragraph, not a headline
        return False
    if a.get("lift"):                        # found verbatim inside the article
        return False
    # Sentence case where a headline belongs. "It was a surreal sight" carries
    # the slug it-was-a-surreal-sight, so the slug is no help — it was minted
    # from the same mistake, and both witnesses repeat it. What still separates
    # them is capitals: the magazine sets headlines in title case, and a line
    # lifted out of a paragraph keeps its sentence case. Only applied to
    # headings long enough to judge and without the punctuation a real headline
    # would carry, so "Repent – for what?" and "Firebrand" are untouched.
    w = ti.split()
    if len(w) >= 4 and not ti.rstrip().endswith(("?", "!", ".", "”", "’", '"')):
        capped = sum(1 for x in w if x[:1].isupper())
        if capped / len(w) < 0.35:
            return False
    head = _norm(ti)
    if len(head) >= 12:
        for field in ("d", "x"):             # the dek, and the opening paragraph
            if _norm(a.get(field)).startswith(head[:60]):
                return False
    return True

def author_key(name):
    """The archive spells the same writer several ways — "Rabbi Greenberg",
    "Rabbi H. Greenberg" — so cap on the surname, not the byline."""
    n = re.sub(r"(rabbi|reb|r\.|rav|ha?rav)", " ", (name or "").lower())
    n = re.sub(r"[a-z]\.", " ", n)          # initials
    n = re.sub(r"[^a-z ]", " ", n).split()
    return n[-1] if n else "?"

def spread(items, cap=2, key="a"):
    """Keep the page from becoming one columnist. Order is preserved; anything
    over the cap for a given writer is dropped."""
    out, seen = [], {}
    for a in items:
        k = author_key(a.get(key))
        if seen.get(k, 0) >= cap:
            continue
        seen[k] = seen.get(k, 0) + 1
        out.append(a)
    return out

def render_landing(data):
    wk = week_for(data)
    # ask for a deeper pool than the page needs, so capping a prolific
    # columnist still leaves real choices underneath rather than forcing a
    # third piece by the same writer
    slugs = pick(data, wk, 24)
    arts = [data["articles"][s] for s in slugs if s in data["articles"]]
    arts = spread(arts, cap=2)
    lead_first = arts[:1]
    arts = lead_first + sorted(arts[1:], key=lambda x: not reads_as_headline(x))
    arts = arts[:9]           # not one columnist's page, and no lifted sentences
    if len(arts) < 7:                             # top back up if the cap bit hard,
        have = {author_key(a.get("a")) for a in arts}       # new writers first
        rest = [data["articles"][s] for s in slugs
                if s in data["articles"] and data["articles"][s] not in arts]
        rest.sort(key=lambda x: (author_key(x.get("a")) in have, not reads_as_headline(x)))
        for a in rest:
            arts.append(a)
            if len(arts) >= 7:
                break
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
    rest = [a for a in arts if a["s"] != lead["s"]][:6]
    if not is_photo(lead):
        lead = dict(lead, _whytag=(getattr(pick, "why", {}) or {}).get(lead["s"], ""))
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
    def eligible(s):
        if s in shown or s not in data["articles"]:
            return False
        tags = set(season.get(s, []))
        return not (tags and not (tags & here))

    # Shleimus HaAretz always has a place on the page — it is a standing
    # concern of the magazine, not an occasional topic.
    ever, cand, used_authors = [], [], {author_key(a.get("a")) for a in arts if a.get("a")}
    shleimus = [data["articles"][s] for s in data["tags"].get("shleimus-ha-aretz", [])
                if eligible(s)]
    for a in sorted(shleimus, key=lambda x: not reads_as_headline(x)):
        ever.append(a); break
    for s in data["evergreen"]:
        if len(ever) >= 6:
            break
        if not eligible(s) or any(e["s"] == s for e in ever):
            continue
        a = data["articles"][s]
        if author_key(a.get("a")) in used_authors:
            continue                              # a writer already on the page
        cand.append(a)
    # A lifted sentence only gets a slot if nothing else can fill it.
    heads = [a for a in cand if reads_as_headline(a)]
    cand = heads + [a for a in cand if a not in heads] if len(heads) < 6 else heads
    cand.sort(key=lambda x: (not reads_as_headline(x), not is_art(x)))  # headlines, then photos
    for a in cand:
        if len(ever) >= 6:
            break
        ever.append(a); used_authors.add(author_key(a.get("a")))
    for want_headline in (True, False):           # fill if the rules left it short
        for s in data["evergreen"]:
            if len(ever) >= 6:
                break
            a = data["articles"].get(s)
            if not a or not eligible(s) or any(e["s"] == s for e in ever):
                continue
            if want_headline and not reads_as_headline(a):
                continue
            ever.append(a)
    kicker = " · ".join(x for x in [("Parshas " + wk["p"]) if wk["p"] else "",
                                    ("Shabbos " + wk["hd"]) if wk["hd"] else ""] if x)

    # Tell the reader why each piece is here this week — "Parshas Re'eh",
    # "Menachem Av" — rather than only naming the department it ran in.
    labels = wk.get("labels", {})
    whyof = getattr(pick, "why", {}) or {}
    def dress(a):
        wt = whyof.get(a["s"], "")
        # a standing strand has no label in the week entry — it belongs to no week
        return dict(a, _season=wk["tags"], _whytag=wt,
                    _why=labels.get(wt, "") or STANDING.get(wt, ""))

    used = set()
    page = LANDING.replace("{{FEATURE}}", feature_html()) \
                  .replace("{{KICKER}}", esc(kicker)) \
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
<link rel="icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAHKUlEQVR4AeybC4hUZRTH/zPrmquVurq0lkmKRoqpEaEFPZCVggJZLYWiEMLQEKQHtZEggb0MQ0MqShEthdJtTTKzx2YJKQnaSvkI0VhdXTVz85G6Ojt1ROE/Z8b7zd373ZlNj/hjzzffd8853//P3JdrEkDaKJ4GYsB/+tvfYilgBhRL+Qt1zYALQhTrh3cDZnQvAVOsjfmqOy1ZAsZX3ot5vBtwMbH9zE8BMyA/nWJbZQbEJm1+ic2A/HSKbZUZEJu0+SW+Mg3IT5uCrDIDCiLzpYtENuCJkkowjScqwPAzgcSXbqVjzPA9v8SN6TIw8hkje2LC7iKyAWEL2vpMBcyATD0KPjIDCi55ZkGnAXy+yxU/N7ULmMVbkmD4eiAxny8lzmzHPZJjgnBnyFyhcx1LVIBZubgzmMlP3wim5TjAZGZ3j5wGuFPYiigKmAFR1PNwrBngQcQoKbIM0OdEnZzviSWe895pMC9WlYHJOj7kc4Lup2JEdwShr1O6vs4n1yWmpe0EmJrne4JZ+mkJGL5eSKzr63q6nywD9AJ/Y8uUSwEzIJcqBfzMDCig2LlKJfU5iu9pJZbzPKOT8PlS4h2HD4Jxrefzr8S6n63HysDofHrMvUqsz8lSg9HH90heDab5yEkEoY+X6wAjGjJ6vX0DtCIFHpsBBRZclzMDtCIFHidn/Z0Cw+cviXU/Tz4zCcznZw8giAXb3wWj8+kxn58lvmv0RDBTP1yAIEbcVgVG9sDoenrMveYTjxpfDUaugwzXlljXs2+AVqTAYzOgwILrcmaAVsTz2JUusgHplpcQRKfyejB8jy2xq8Fre3UGw7lyxZUD+4Bx5a/s1Q1Mrpz8Wek/q8Hc0LcEjKueno9sgE5o43AKmAHh9PK+2gzwLmm4hFkG8D2sxDpd074UGJTejDBIzjDo+r7H+j2Pay/pvmVg+l3XCkaua4yr36Rrgc3Hq4AZEK++zuxmgFOieBdkGcDvUSTm9zASHzvSCmb2uAaE4YFHHkcQfP6U+M7bU2BccvA9ucR8jy8xv7fJFb8/eTuCmD3xFJi1X6fADLnvQTA3DR8FRvefZYBeYON4Fbg8DYhXM6/ZzQCvcoZPlmXAHw0bwfxU/wmYed8vRhS+Wv4RmI21dWD0M8Kw6VPBJPZ/BgZfLgPz0MwxYPjfpyXm2u2JWYtc8bZ1q8GwlhJri7IM0AtsHK8CZkC8+jqzmwFOieJdENqAfUdrwexvPQqG5yRuOjQFjH4GcG0v2WkgmPT145DB2EVIE8luo8G48ut+Vh6eBKauZSkyOLUedcTKltfA6GuYq35oA1wJbT6cAmZAOL28rzYDvEsaLqHTAHkfwyTOfgOm7WQ9GJ6TmO/Rz8fh+svILXXO56B7/+SeVWDazu0CE7JcxjOF1OLcEuNMI5jEngYwYes5Dcg/oa1sjwJmQHtU83iMGeBRzPakCm1AunQMGL7nljjR43Uw6QnfgWnedQCMq2nJySSGVYNJ9x8Ohp8ZJHbl514k5l4lxtC5YLgXidtumQbGVU/PhzZAJ7BxNAXMgGj6RT7aDIgsYbQEoQ2o7vEYmLGlfRBEddndYH7Z8i0Y17uTP+sXgjnUuwrM4eMVYA41fwHGJQ/3IjH3KnHQ3mRO1jD8zCSxq35oA1wJbT6cAmZAOL28rzYDIkoa9fAOb8DyBTvB6A33vqYrmNpnfwQDz3/kvB6E65qm2+nwBuiGL7exGVBkR82Ajm7A+OkPg3n1gxlgXnnjUTAL185CGFz7bx20BszZlh1gDuzdDIbXSuzK7+p1xc4lYBatrgIzZ00NGNZCYld9+wa4FIp53gyIWWBXejPApVDM804DBgzuC2bIhMFgRtyfAlN+z70IZGR/lBOu/TVtPgnmndEfIwheK7HOvylxGkyvkUkwuveSfv3BJCuvAqPXdyofAEbX12OnAfoAG/tV4P9pgF8NiprNDCiq/IDTgHN/7QaDDcvBpLfWgeHfmTkfr5sDEPK7NYxr/4mmc2Dkd/wZ/f98ea3ErvzpDT+DSe6YDybVuAcM71Vi3pvErJXErvpOA1wJbD6aAmZANP0iH20GRJYwWgLvBqQOpsC42gt6ty5zie49wchnjCu/nr8j3QWMnm9rPgNGz/seezfAd4OXez4zoMgOmwEd3YDGg53BbNs7FMxvZ14As/OH38HwWol/3TQIjO/98/VCYr5eSKzrSU9B8F4k5r1KvLWhKxjWSmJdT49DfAP0oTb2oYAZ4EPFCDnMgAji+TjUaUDtvBVg3poyF0HcOrkGjF778lOzwCxJNYPxsamgHKvSJ8Do/vSY9yIx9y7xzJplYMa+PR9MUC8y5zRAFhnxKWAGxKdtXpnNgLxkim9RlgF8Pm5PrFvVOfj8K7Fr/Zvrd4PR+fSY10qs5131XOul5yBc+fV8lgF6gY3jVcAMiFdfZ3YzwCFR3NP/AgAA///uMxayAAAABklEQVQDAPahuMqaeBpcAAAAAElFTkSuQmCC">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beis Moshiach — Moshiach, Geula &amp; Chassidus</title>
<meta name="description" content="A weekly reading from the Beis Moshiach archive — chosen for this week's parsha and the Chabad calendar, from 3,541 articles.">
<!-- The imago badge holds the bottom-right corner (18px up, 37px tall), so the
     install chip sits above it and leaves it clear once the chip is gone. -->
<meta name="pwa-install-offset" content="66">
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
  /* the piece's own opening, under the magazine's dek */
  .lead-txt .open{font-size:.94rem;line-height:1.65;color:var(--ink-soft);opacity:.86;
        margin:0 0 1.1rem;max-width:48ch;border-left:2px solid var(--parchment-edge);
        padding-left:.9rem}
  .meta{font-family:var(--mono);font-size:.7rem;letter-spacing:.04em;color:var(--royal);margin:0}
  .row{display:grid;align-items:start;grid-template-columns:repeat(3,1fr);gap:clamp(1rem,2.5vw,1.8rem);
       padding-bottom:clamp(2rem,5vw,3.5rem)}
  @media(max-width:900px){.row{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:560px){.row{grid-template-columns:1fr}}
  .card{display:block;color:inherit}
  .card figure{margin:0 0 .8rem;overflow:hidden;border-radius:3px;background:var(--parchment-deep)}
  .card img{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:cover;
        object-position:center;background:var(--parchment-deep);transition:transform .7s var(--ease)}
  .card img.port{object-position:center 18%}   /* keep heads in frame */
  .card:hover img{transform:scale(1.05)}
  .card h3{font-family:var(--display);font-weight:600;font-size:1.12rem;line-height:1.25;
        margin:0 0 .4rem;color:var(--ink)}
  .card:hover h3{color:var(--royal)}
  /* A headline alone asks the reader to gamble. Give them the magazine's own
     opening lines and let the writing do the inviting. Clamped so a long dek
     and a short one still make a level row. */
  .card .blurb{font-size:.9rem;line-height:1.55;color:var(--ink-soft);margin:0 0 .55rem;
        display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;
        line-clamp:3;overflow:hidden}
  /* the type card has the whole box to itself, so it can afford to say more */
  .card.txt .blurb{-webkit-line-clamp:7;line-clamp:7;font-size:.94rem;margin-bottom:.8rem}
  @media(max-width:560px){.card .blurb{-webkit-line-clamp:4;line-clamp:4}}
  /* No picture worth printing? Let the type carry it — a set-in card rather
     than a columnist's headshot stretched into a photograph. */
  .card.txt{display:flex;flex-direction:column;justify-content:center;align-self:start;
        padding:1.1rem 1.2rem;background:var(--parchment-deep);border:1px solid var(--parchment-edge);
        border-left:3px solid var(--gold-bright);border-radius:3px;
        transition:border-color .2s,transform .3s var(--ease)}
  .card.txt:hover{transform:translateY(-2px);border-color:var(--royal);border-left-color:var(--royal)}
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
  /* The editor's slot. Deliberately quieter than the lead — picture smaller,
     heading a step down — so it reads as a second invitation rather than
     competing with the week's own story for the same eye. */
  .feature{display:grid;grid-template-columns:.8fr 1.2fr;gap:clamp(1.2rem,3vw,2.4rem);
        align-items:center;text-decoration:none;color:inherit;
        padding-bottom:clamp(1.6rem,4vw,2.6rem);border-bottom:1px solid var(--rule)}
  .feature figure{margin:0;overflow:hidden;border-radius:3px;background:var(--parchment-deep)}
  .feature img{display:block;width:100%;height:auto;
        transition:transform 1.2s var(--ease)}
  .feature:hover img{transform:scale(1.03)}
  .feature h2{font-family:var(--display);font-weight:700;
        font-size:clamp(1.5rem,3vw,2.3rem);line-height:1.05;letter-spacing:-.015em;
        margin:0 0 .7rem;color:var(--ink)}
  .feature:hover h2{color:var(--royal)}
  .feature .dek{margin-bottom:.7rem}
  @media(max-width:820px){.feature{grid-template-columns:1fr}.feature figure{order:-1}}
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
  <nav><a href="/topics">Topics</a><a href="/parsha">Parsha</a><a href="/collections">Collections</a><a href="/science/">Convergence</a>
    <a href="/archives">Archives</a><a href="/search">Search</a><a class="langsw" href="/he/">עברית</a></nav>
</div></header>
<main class="wk" data-week="{{WEEK}}">
  <p class="kick" id="kick">This week · {{KICKER}}</p>
  <div id="lead">{{LEAD}}</div>
{{FEATURE}}
  <p class="kick">More for this week</p>
  <div class="row reveal" id="cards">{{CARDS}}</div>
  <p class="kick" id="weekpoll-kick">The week&rsquo;s question</p>
  <!-- Filled by assets/poll.js from /api/poll. Both this and the kicker above
       remove themselves on any week the editor has not set a question, so the
       page never announces an absence. Written by admin-poll.html. -->
  <section id="weekpoll" class="reveal" aria-label="The week&rsquo;s question" hidden></section>
  <p class="kick">From the archive</p>
  <div class="row reveal" id="ever">{{EVER}}</div>
  <p class="kick">Ways in</p>
  <nav class="ways reveal">
    <a href="/collections">Collections</a><a href="/archives">The archive · 3,541 articles</a>
    <a href="/topics">Topics</a><a href="/parsha">By parsha</a><a href="/search">Search</a>
    <a href="/science/">Moshiach &amp; Science</a>
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
    if(list.length<13&&d.evergreen.length){
      var off=Math.floor(Date.parse(wk.w)/6048e5)%d.evergreen.length;
      for(var j=0;j<d.evergreen.length&&list.length<13;j++){
        var s=d.evergreen[(off+j)%d.evergreen.length];
        if(seen[s]) continue;
        if(!inSeason(s)) continue;               /* out of season? wait its turn */
        seen[s]=1;list.push(s);
      }
    }
    var arts=list.map(function(s){var a=d.articles[s];
      return a?Object.assign({},a,{_why:why[s]||''}):null;}).filter(Boolean);
    /* the same rules the builder applies, so a week that turns over without a
       rebuild does not slide back to one columnist and lifted sentences */
    var akey=function(n){n=(n||'').toLowerCase().replace(/\b(rabbi|reb|rav|harav)\b/g,' ')
        .replace(/\b[a-z]\./g,' ').replace(/[^a-z ]/g,' ').trim().split(/\s+/);
      return n.length?n[n.length-1]:'?';};
    var headline=function(a){var ti=(a.t||'').trim();
      if(!ti||ti.split(/\s+/).length<2) return false;
      if(ti[0]===ti[0].toLowerCase()&&ti[0]!==ti[0].toUpperCase()) return false;
      if(/^(it|he|she|they|there|we|this|that)\s+(was|were|is|are|had|have|has|will|would|could|began|went)/i.test(ti)) return false;
      if(/[?!]$/.test(ti)) return true;
      return ti.length<=45||ti.split(/\s+/).length<=8;};
    var seenA={},kept=[];
    arts.forEach(function(a){var k=akey(a.a);
      if((seenA[k]||0)>=2) return; seenA[k]=(seenA[k]||0)+1; kept.push(a);});
    if(kept.length>1){var h=kept.slice(1).sort(function(x,y){
      return (headline(x)?0:1)-(headline(y)?0:1);}); kept=[kept[0]].concat(h);}
    arts=kept;
    if(!arts.length) return;
    var esc=function(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
    var meta=function(a){return [a.a,a.c,a.i?('#'+a.i):''].filter(Boolean).join(' · ');};
    var FB='storage/landing/topics.jpg';
    var used={};
    var art=function(a){return a.img&&a.img.indexOf('category-pics')<0&&a.w>=400;};
    var AM=d.art||{season:{},dept:{}};
    var LB=wk.labels||{};
    var whyOf=function(a){return LB[a._why||'']||'';};
    var chip=function(a){var w=whyOf(a);
      return '<span class="why'+(w?'':' plain')+'">'+esc(w||a.c||'From the archive')+'</span>';};
    /* Beis Moshiach separates dek clauses with an asterisk; set it as a
       middot, which is what that break looks like on screen */
    var sep=function(s){return s.replace(/ \*+ /g,' · ');};
    /* the magazine's own dek, verbatim; a type card gets the opening too */
    var blurb=function(a,txt){var s=a.d||a.x||'';
      if(a.d&&a.x&&(txt||a.d.length<110)) s=a.d+' * '+a.x;
      return s?'<p class="blurb">'+sep(esc(s))+'</p>':'';};
    var picCard=function(a,src){ used[src]=1;
      return '<a class="card" href="articles/'+esc(a.s)+'.html">'+
        '<figure><img src="'+esc(src)+'" alt="" loading="lazy"></figure>'+
        chip(a)+'<h3>'+esc(a.t)+'</h3>'+blurb(a)+'<p class="meta">'+esc(meta(a))+'</p></a>';};
    var artFor=function(a){        /* the piece's own reason first, then the week's, then dept */
      var o=[],own=a._why,push=function(f){if(f&&o.indexOf(f)<0)o.push(f);};
      push(AM.season[own]);                       /* the date it is here for */
      push(AM.dept[(a.c||'').trim()]);            /* else what it is */
      return o;};   /* never another date's art — it would contradict the badge */
    var card=function(a){
      if(art(a)&&!used[a.img]) return picCard(a,a.img);
      var cand=artFor(a);
      for(var i=0;i<cand.length;i++){ if(!used[cand[i]]) return picCard(a,cand[i]); }
      return '<a class="card txt" href="articles/'+esc(a.s)+'.html">'+
        chip(a)+'<h3>'+esc(a.t)+'</h3>'+blurb(a,1)+'<p class="meta">'+esc(meta(a))+'</p></a>';};
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
      '<div class="lead-txt">'+chip(L)+'<h1>'+esc(L.t)+'</h1><p class="dek">'+sep(esc(L.d||''))+'</p>'+
      (L.x?'<p class="open">'+esc(L.x)+'</p>':'')+
      '<p class="meta">'+esc(meta(L))+'</p></div></a>';
    document.getElementById('cards').innerHTML=arts.slice(1,7).map(card).join('');
    main.dataset.week=wk.w;
  }).catch(function(){/* the rendered week stands */});
})();
</script>
<script>
/* Offer the app where the other ways in are listed. The link only appears when
   the browser says the site is actually installable.

   pwa.js owns the install event and the record of having asked, so this defers
   to it rather than catching beforeinstallprompt itself — two listeners racing
   for one event means whichever fires second calls prompt() on an event already
   spent, and the corner chip and this link would forget each other's answer. */
/* pwa.js is deferred, so it has not run yet at this point in the body — a
   deferred script executes after parsing but before DOMContentLoaded, which
   is exactly the moment to look for it. */
addEventListener('DOMContentLoaded',function(){
  var a=document.getElementById('installapp'); if(!a) return;
  var pwa=window.pwaInstall;
  if(!pwa||pwa.standalone) return;                 // nothing to offer
  pwa.onAvailable(function(){ a.hidden=false; });
  a.addEventListener('click',function(e){
    e.preventDefault();
    a.hidden=true;                                  // asked once, either way
    pwa.prompt();
  });
  addEventListener('appinstalled',function(){ a.hidden=true; });
});
</script>
<script src="assets/poll.js" defer></script>
<script src="https://dreamsitedesign.com/imago-dreamsite.js" defer
        data-domain="DREAMSITEDESIGN.COM"
        data-href="https://dreamsitedesign.com"
        data-perch="DREAMSITEDESIGN.COM"
        data-wing="#FDCB40" data-wing-deep="#8A5B00" data-spot="#0042AF"
        data-paper="#FEF1D0" data-ink="#0A0A0B"></script>
</body></html>"""

if __name__ == "__main__":
    main()
