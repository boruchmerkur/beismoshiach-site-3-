# -*- coding: utf-8 -*-
"""Decide which edition a Scribd upload is, from the page's own extracted text.

The first attempt read only the document description, which is wrong often
enough to matter: three Hebrew issues got downloaded and indexed as English
before the mistake showed up. The description is one short field and some
uploads carry the wrong one.

This reads the whole page instead and counts Hebrew letters against Latin
words across everything Scribd exposes — title, description and the text
preview. A scanned issue has no preview at all, so those are reported as
"scan" rather than guessed at; for those the only honest answer is to look.

Validate mode checks the rule against issues whose language is already known
from the downloaded file, so the rule is measured before it is trusted.
"""
import io, json, os, re, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join(ROOT, "scribd_lang2.json")

# settled by opening the file: text layer, thousands of characters, one script
KNOWN = {907: "en", 922: "en", 923: "en", 928: "en", 934: "en",
         938: "en", 961: "en", 968: "en", 879: "en",
         874: "he", 882: "he", 894: "he"}


def fetch(doc_id):
    url = "https://www.scribd.com/document/%s" % doc_id
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def classify(html):
    """Hebrew letters against English words, over everything the page exposes."""
    # \uXXXX escapes in the embedded JSON hide the Hebrew from a naive count
    txt = re.sub(r"\\u([0-9a-fA-F]{4})",
                 lambda m: chr(int(m.group(1), 16)), html)
    body = re.sub(r"<script.*?</script>", " ", txt, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    he = len(re.findall(r"[א-ת]", body))
    # words, not letters: the page chrome is full of English single characters
    en = len(re.findall(r"\b[A-Za-z]{4,}\b", body))
    if he < 25 and en < 400:
        return "scan", he, en
    return ("he" if he > en else "en"), he, en


def main():
    ids = {}
    for line in io.open(os.path.join(ROOT, "scribd_gap.txt"), encoding="utf-8"):
        n, url = line.split("\t")
        ids[int(n)] = url.strip().rsplit("/", 2)[-2]

    if "--validate" in sys.argv:
        ok = bad = 0
        for n, want in sorted(KNOWN.items()):
            if n not in ids:
                continue
            got, he, en = classify(fetch(ids[n]))
            hit = (got == want)
            ok, bad = ok + hit, bad + (not hit)
            print("#%-5d want %-4s got %-5s he=%-6d en=%-6d %s"
                  % (n, want, got, he, en, "" if hit else "   <-- MISS"))
            time.sleep(0.7)
        print("\n%d right, %d wrong" % (ok, bad))
        return

    out = json.load(io.open(OUT, encoding="utf-8")) if os.path.isfile(OUT) else {}
    for i, n in enumerate(sorted(ids), 1):
        if str(n) in out:
            continue
        try:
            got, he, en = classify(fetch(ids[n]))
        except Exception as e:
            print("#%-5d %s" % (n, e)); continue
        out[str(n)] = {"doc": ids[n], "lang": got, "he": he, "en": en}
        print("#%-5d %-5s he=%-6d en=%-6d" % (n, got, he, en))
        if i % 10 == 0:
            json.dump(out, io.open(OUT, "w", encoding="utf-8"), indent=1)
        time.sleep(0.7)
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), indent=1)
    from collections import Counter
    print("\n", Counter(v["lang"] for v in out.values()))


if __name__ == "__main__":
    main()
