"""The side column on every article page: the author, his other pieces, this week's parsha.

    PYTHONUTF8=1 python tools/build_side.py

His ruling 2026-11-10 ("Right, use the space"): an article's reading column no longer sits
in an empty screen; the margin carries the author and more of his work. Built as data plus
one script (assets/side.js, loaded by assets/comments.js, which every article already
loads), so no article file changes. That matters: articles/*.html hold the uncommitted SEO
pass, which is released in batches on purpose and must not ride along with anything else.

Reads each article's eyebrow line only (author, department, issue, date) and its title.
Article text is never read into the output, let alone changed.

Writes:
  assets/side/a/<author-slug>.json   {name, img, items: [{s, t, d}]} newest first, up to 40
  assets/side/week.json              this week's and next week's parsha, with a few articles
Re-run when articles are added; the landing pass's weekly.json supplies the parsha schedule.
"""
import collections, datetime, html, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "articles")
OUT = os.path.join(ROOT, "assets", "side")

EYEBROW = re.compile(r'<div class="entry-eyebrow">(.*?)</div>', re.S)
TITLE = re.compile(r'<h1 class="entry-title">(.*?)</h1>', re.S)
AU = re.compile(r'<span class="au">(.*?)</span>', re.S)
DATE = re.compile(r'<span>([A-Z][a-z]+ \d{1,2}, \d{4})</span>')
PIC = re.compile(r'src="(?:\.\./)+storage/(?:\.\./storage/)?(category-pics/[^"]+)"')


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"


def main():
    by = collections.defaultdict(list)
    pics = collections.defaultdict(collections.Counter)
    n = 0
    for f in sorted(os.listdir(ART)):
        if not f.endswith(".html"):
            continue
        h = open(os.path.join(ART, f), encoding="utf-8", errors="replace").read()
        eb, ti = EYEBROW.search(h), TITLE.search(h)
        if not eb or not ti:
            continue
        au = AU.search(eb.group(1))
        if not au:
            continue
        name = text(au.group(1))
        if not name:
            continue
        dm = DATE.search(eb.group(1))
        try:
            d = datetime.datetime.strptime(dm.group(1), "%B %d, %Y").date().isoformat() if dm else ""
        except ValueError:
            d = ""
        by[name].append({"s": f[:-5], "t": text(ti.group(1)), "d": d})
        b0 = h.find('class="entry-body"')
        for p in PIC.findall(h[b0:b0 + 3000] if b0 > 0 else ''):   # the author photo opens the body
            pics[name][p] += 1
        n += 1
    os.makedirs(os.path.join(OUT, "a"), exist_ok=True)
    for name, items in by.items():
        items.sort(key=lambda x: x["d"], reverse=True)
        img = pics[name].most_common(1)[0][0] if pics[name] else ""
        json.dump({"name": name, "img": ("/storage/" + img) if img else "", "items": items[:40]},
                  open(os.path.join(OUT, "a", slug(name) + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))

    # This week's parsha, from the landing pass's schedule, with the articles it lists.
    w = json.load(open(os.path.join(ROOT, "assets", "weekly.json"), encoding="utf-8"))
    titles = {k: v["t"] for k, v in w["articles"].items()}
    weeks = []
    for e in w.get("schedule", []):
        tag = e.get("ptag")
        arts = [{"s": s, "t": titles[s]} for s in w.get("tags", {}).get(tag, []) if s in titles][:4]
        weeks.append({"w": e["w"], "label": e.get("labels", {}).get(tag) or ("Parshas " + e.get("p", "")),
                      "tag": tag, "items": arts})
    json.dump({"weeks": weeks}, open(os.path.join(OUT, "week.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"side: {n} articles, {len(by)} authors, {sum(1 for k in pics if pics[k])} with a photo, {len(weeks)} parsha weeks")


if __name__ == "__main__":
    main()
