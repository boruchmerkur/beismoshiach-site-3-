# -*- coding: utf-8 -*-
"""Index the archive's science writing into assets/science.json.

Convergence ran as its own site with a live RSS wire and a section called The
Column that never rendered, because it required three essays arguing FROM a
scientific finding and only one qualified. That was the wrong way round: the
archive already carries a Moshiach & Science department, and those pieces are
the thing the wire exists to sit beside.

This writes one row per article, in the same shape the landing page's cards
already use, plus the Convergence reading each piece reads against. The landing
page and /science/ both render from it, so a science card and a wire card are
the same object on the page and can be interleaved.

Text is copied out of the archive byte for byte. Nothing here rewrites,
corrects or normalises a single character of an article — the only change made
to any string is collapsing runs of whitespace for display, and U+00A0 is left
alone so a title that was typeset with a non-breaking space keeps it.

Re-run when articles are added:  python3 tools/build_science.py
"""
import os, re, io, json, html, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "articles")
OUT = os.path.join(ROOT, "assets", "science.json")

# The department is the spine of the set. Everything else is an addition that
# has to earn its place, because "mentions a scientist" is not "about science".
DEPT = "moshiach-science"

# Bylines that belong to the subject wherever they are filed.
BYLINE = re.compile(r"(Silman|Gotfryd|Branover)", re.I)

# A piece filed elsewhere is admitted only on a concrete term in its title or
# pull-quote. Soft words (research, study, professor, knowledge) are excluded
# on purpose: a Chassidus magazine uses them about everything.
HARD = re.compile("|".join([
    r"physic|quantum|relativit|particle|cosmolog|astronom|galax|telescop",
    r"biolog|genome|genetic|DNA|neuroscien|medicine|medical|surger|laser",
    r"technolog|comput|robot|satellite|space (flight|program|travel)",
    r"chemistr|molecul|atom|nuclear|energy|electric|magnet",
    r"evolution|dinosaur|fossil|geolog|archaeolog",
    r"science|scientist|scientific|laborator|experiment|Nobel",
]), re.I)

# The six readings, carried over from Convergence's wire.js unchanged, so a
# card built here and a card built from a feed are tagged by the same rule.
READINGS = [
    ("daas", "ומלאה הארץ דעה", "Yeshayahu 11:9",
     r"artificial intelligence|language model|machine learning|translat|archive|open access|dataset|literac|educat|knowledge|library|search engine|information"),
    ("techiya", "הנה אני פתח את קברותיכם", "Yechezkel 37:12",
     r"stem cell|regenerat|reprogram|longevity|lifespan|aging|ageing|senescen|tissue|organoid|transplant|cryo|DNA repair|gene therapy|CRISPR|resurrect|techiy|revival"),
    ("echad", "ה׳ אחד", "Devarim 6:4",
     r"unified|unification|grand unif|quantum gravity|standard model|symmetr|fundamental force|theory of everything|entangl|oneness|unity"),
    ("shefa", "לא רעב ולא מלחמה", "Rambam, Melachim 12:5",
     r"crop yield|harvest|\bcrops?\b|fusion|solar|battery|desalinat|famine|food secur|abundance|fertili[sz]er|manufactur|vaccine|malaria|drought|plenty"),
    ("bereishis", "בראשית ברא", "Bereishis 1:1",
     r"cosmolog|big bang|early universe|telescope|JWST|Webb|galax|cosmic|dark energy|dark matter|exoplanet|black hole|creation|beginning of everything"),
    ("geula", "וכתתו חרבותם לאתים", "Yeshayahu 2:4",
     r"swords into plowshares|plowshare|disarm|ceasefire|peace (deal|treaty|accord)|missile|weapon|war\b|military|cruise missile"),
]
READINGS = [(k, h, c, re.compile(rx, re.I)) for k, h, c, rx in READINGS]


def txt(s):
    """Unescape entities and collapse ASCII whitespace. U+00A0 is preserved."""
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[ \t\r\n\f\v]+", " ", s)
    return s.strip()


def one(tag_re, s):
    m = tag_re.search(s)
    return txt(m.group(1)) if m else ""


RE_ISS = re.compile(r'<a class="iss"[^>]*>#?([^<]*)</a>')
RE_AU = re.compile(r'<span class="au">([^<]*)</span>')
RE_DEPT = re.compile(r'<a class="dept" href="category/([^"]+)\.html">([^<]*)</a>')
RE_DATE = re.compile(r'<a class="dept"[^>]*>[^<]*</a>\s*[^<]*<span>([^<]*)</span>')
RE_TITLE = re.compile(r'<h1 class="entry-title">(.*?)</h1>', re.S)
RE_PULL = re.compile(r'<p class="entry-pull">(.*?)</p>', re.S)
RE_OGD = re.compile(r'<meta property="og:description" content="([^"]*)"')
RE_OGI = re.compile(r'<meta property="og:image" content="([^"]*)"')
RE_BODY = re.compile(r'<div class="entry-body">(.*?)</article>', re.S)
RE_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def local_img(u):
    """og:image is absolute; the landing page wants a repo-relative path."""
    if not u:
        return ""
    u = html.unescape(u)
    i = u.find("storage/")
    if i < 0:
        return ""
    p = u[i:]
    return p if os.path.isfile(os.path.join(ROOT, p.replace("/", os.sep))) else ""


def reading_for(text):
    for k, h, c, rx in READINGS:
        if rx.search(text):
            return {"k": k, "h": h, "c": c}
    return None


def read_article(slug):
    p = os.path.join(ART, slug + ".html")
    if not os.path.isfile(p):
        return None, ""
    s = io.open(p, encoding="utf-8").read()

    dm = RE_DEPT.search(s)
    dept_slug = dm.group(1) if dm else ""
    dept = txt(dm.group(2)) if dm else ""
    title = one(RE_TITLE, s)
    if not title:
        return None, s
    pull = one(RE_PULL, s) or one(RE_OGD, s)
    body = one(RE_BODY, s)
    author = one(RE_AU, s)
    date = one(RE_DATE, s)
    issue = one(RE_ISS, s)

    return {
        "s": slug,
        "t": title,
        "a": author,
        "dept": dept,
        "deptSlug": dept_slug,
        "date": date,
        "year": (RE_YEAR.search(date).group(0) if RE_YEAR.search(date) else ""),
        "iss": issue,
        "blurb": pull[:420],
        "img": local_img(one(RE_OGI, s)),
        "read": reading_for(title + " " + pull + " " + body[:4000]),
    }, s


def main():
    slugs = sorted(
        f[:-5] for f in os.listdir(ART)
        if f.endswith(".html") and os.path.isfile(os.path.join(ART, f))
    )

    rows, why = [], {}
    for slug in slugs:
        # Read the whole file. An earlier version pre-filtered on the first 6kB
        # to save time and lost 10 of the 28 department pieces: every page opens
        # with a base64 favicon, so the eyebrow that names the department can sit
        # past any fixed window. The archive is 3,600 files and this takes a
        # couple of minutes; the build runs when articles are added, not often.
        a, src = read_article(slug)
        if not a:
            continue
        body_has = BYLINE.search(src)
        if a["deptSlug"] == DEPT:
            a["why"] = "department"
        elif BYLINE.search(a["a"]):
            a["why"] = "byline"
        elif body_has and HARD.search(a["t"] + " " + a["blurb"]):
            # Gotfryd and Branover are written ABOUT far more often than they
            # are bylined, so a piece that names one and is otherwise about
            # science belongs here too.
            a["why"] = "subject"
        else:
            continue
        why[a["why"]] = why.get(a["why"], 0) + 1
        rows.append(a)

    rows.sort(key=lambda r: (r["why"] != "department", -int(r["iss"] or 0)))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps({"built": "", "count": len(rows), "items": rows},
                   ensure_ascii=False, indent=1)
    )

    tagged = sum(1 for r in rows if r["read"])
    withimg = sum(1 for r in rows if r["img"])
    print("science.json: %d articles (%s)" % (len(rows), ", ".join(
        "%s %d" % kv for kv in sorted(why.items()))))
    print("  %d carry a picture, %d read against a source" % (withimg, tagged))
    for r in rows[:12]:
        print("   %-9s %-6s %-52s %s" % (
            r["why"], "#" + (r["iss"] or "?"), r["t"][:52],
            (r["read"] or {}).get("c", "")))


if __name__ == "__main__":
    main()
