# -*- coding: utf-8 -*-
"""Link the parts of a multi-part piece to each other on the articles.

The landing now shows a series once, as its opening part. That only helps if
the reader can get from part one to part two once he is there, so each member
page gets a strip naming every part and linking the others.

The series map is read from assets/weekly.json, which build_weekly.py writes,
so this cannot drift from what the landing believes. Re-runnable: an existing
strip is replaced rather than stacked.
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARK = "<!--series-->"
STRIP = (MARK + '<nav class="series" aria-label="The parts of this piece">'
         '<span class="sr-kick">This piece runs in {n} parts</span><ol>{items}</ol>'
         '</nav>')


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def main():
    data = json.load(io.open(os.path.join(ROOT, "assets", "weekly.json"),
                             encoding="utf-8"))
    parts_of, arts = data.get("parts", {}), data["articles"]
    if not parts_of:
        print("no series in weekly.json — nothing to link")
        return

    written = 0
    for head, ordered in sorted(parts_of.items()):
        names = [(n, s, (arts.get(s) or {}).get("t") or s) for n, s in ordered]
        for n, slug, _ in names:
            path = os.path.join(ROOT, "articles", slug + ".html")
            if not os.path.isfile(path):
                print("  missing: %s.html" % slug)
                continue
            items = "".join(
                ('<li class="here"><span>Part {k}</span></li>' if k == n else
                 '<li><a href="{s}.html">Part {k}</a></li>').format(
                    k=k, s=esc(s2)) for k, s2, _t in names)
            strip = STRIP.format(n=len(names), items=items)

            t = io.open(path, encoding="utf-8", errors="replace").read()
            t = re.sub(re.escape(MARK) + r'<nav class="series".*?</nav>', "", t,
                       flags=re.S)
            if "</article>" not in t:
                print("  no </article>: %s" % slug)
                continue
            t = t.replace("</article>", "</article>" + strip, 1)
            io.open(path, "w", encoding="utf-8", newline="").write(t)
            written += 1
        print("%s: %s" % (head, " -> ".join("Part %d" % n for n, _s, _t in names)))
    print("linked %d article pages" % written)


if __name__ == "__main__":
    main()
