# -*- coding: utf-8 -*-
"""Pull every remaining Scribd upload's cover into contact sheets.

Two text-based attempts at telling the editions apart have now been wrong.
The description is a single field and some uploads carry the wrong one; the
page text is drowned by 67,000 words of Scribd's own chrome, identical on
every document. Both said #943, #944 and #941 were English. Their covers are
Hebrew.

The cover cannot lie about it, so the covers get looked at. This fetches the
og:image thumbnail for each document and tiles them sixteen to a sheet with
the issue number over each, which is a few seconds of looking instead of a
guess that has to be undone later.
"""
import io, json, os, re, sys, time, urllib.request
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.environ.get("CLAUDE_SCRATCH") or os.path.join(ROOT, ".covers")
UA = {"User-Agent": "Mozilla/5.0"}
COLS, ROWS = 4, 4
W, H, PAD = 300, 380, 24


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=timeout) as r:
        return r.read()


def cover_url(doc_id):
    html = get("https://www.scribd.com/document/%s" % doc_id).decode("utf-8", "replace")
    m = re.search(r'og:image" content="([^"]+)"', html)
    return m.group(1) if m else None


def main():
    want = [int(a) for a in sys.argv[1:] if a.isdigit()]
    ids = {}
    for line in io.open(os.path.join(ROOT, "scribd_gap.txt"), encoding="utf-8"):
        n, url = line.split("\t")
        ids[int(n)] = url.strip().rsplit("/", 2)[-2]

    held = {x["n"] for x in json.load(io.open(
        os.path.join(ROOT, "assets", "editions.json"), encoding="utf-8"))["issues"]
        if x["lang"] == "en"}
    todo = sorted(want or [n for n in ids if n not in held])

    os.makedirs(SCRATCH, exist_ok=True)
    for n in todo:
        p = os.path.join(SCRATCH, "cv-%d.jpg" % n)
        if os.path.isfile(p) and os.path.getsize(p) > 5000:
            continue
        try:
            u = cover_url(ids[n])
            if u:
                io.open(p, "wb").write(get(u))
                print("  #%d %.0f KB" % (n, os.path.getsize(p) / 1024))
            else:
                print("  #%d no cover" % n)
        except Exception as e:
            print("  #%d %s" % (n, e))
        time.sleep(0.5)

    per = COLS * ROWS
    sheets = []
    for s in range(0, len(todo), per):
        batch = todo[s:s + per]
        sheet = Image.new("RGB", (W * COLS, (H + PAD) * ROWS), "white")
        d = ImageDraw.Draw(sheet)
        for i, n in enumerate(batch):
            x, y = (i % COLS) * W, (i // COLS) * (H + PAD)
            d.text((x + 6, y + 6), "#%d" % n, fill="black")
            p = os.path.join(SCRATCH, "cv-%d.jpg" % n)
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((W - 10, H - 10))
                sheet.paste(im, (x + 5, y + PAD - 4))
            except Exception:
                d.text((x + 6, y + 60), "no cover", fill="red")
        out = os.path.join(SCRATCH, "sheet-%02d.png" % (s // per + 1))
        sheet.save(out)
        sheets.append(out)
        print("wrote %s  (%s)" % (out, ", ".join("#%d" % n for n in batch)))
    print("\n%d covers, %d sheets" % (len(todo), len(sheets)))


if __name__ == "__main__":
    main()
