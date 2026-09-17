# -*- coding: utf-8 -*-
"""Work out which Scribd uploads are the English edition and which the Hebrew.

The uploads are slugged with the issue number alone, so the slug says nothing
about which of the two editions it is — both run their own numbering and both
sit on the same account. Ranking them by the English site's article counts
therefore sent half the list to Hebrew issues.

The document's own description settles it: the Hebrew edition carries
"עניני משיח וגאולה", the English "Heralding the imminent arrival of Moshiach".
"""
import io, json, os, re, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join(ROOT, "scribd_lang.json")


def describe(doc_id):
    url = "https://www.scribd.com/document/%s" % doc_id
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=30) as r:
            t = r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)
    m = (re.search(r'"description":"(.{0,800}?)","', t)
         or re.search(r'<meta name="description" content="([^"]{0,800})', t))
    if not m:
        return None, "no description"
    s = m.group(1)
    # the JSON carries Hebrew as \uXXXX; without decoding it reads as ASCII
    try:
        s = json.loads('"%s"' % s.replace('\\"', '"').replace('"', '\\"'))
    except Exception:
        pass
    return s, None


def lang_of(desc):
    he = len(re.findall(r"[֐-׿]", desc))
    en = len(re.findall(r"[A-Za-z]", desc))
    if he and he >= en:
        return "he"
    if en:
        return "en"
    return "?"


def main():
    src = os.path.join(ROOT, "scribd_gap.txt")
    todo = []
    for line in io.open(src, encoding="utf-8"):
        n, url = line.split("\t")
        todo.append((int(n), url.strip().rsplit("/", 2)[-2]))

    known = {}
    if os.path.isfile(OUT):
        known = json.load(io.open(OUT, encoding="utf-8"))

    for i, (n, doc) in enumerate(todo, 1):
        if str(n) in known:
            continue
        desc, err = describe(doc)
        if err:
            print("  #%-5d %s" % (n, err)); continue
        L = lang_of(desc)
        known[str(n)] = {"doc": doc, "lang": L, "desc": desc[:90]}
        print("#%-5d %s  %s" % (n, L, desc[:70].replace("\n", " ")))
        if i % 10 == 0:
            json.dump(known, io.open(OUT, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        time.sleep(0.7)

    json.dump(known, io.open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    en = [k for k, v in known.items() if v["lang"] == "en"]
    he = [k for k, v in known.items() if v["lang"] == "he"]
    print("\nEnglish: %d    Hebrew: %d    unclear: %d"
          % (len(en), len(he), len(known) - len(en) - len(he)))


if __name__ == "__main__":
    main()
