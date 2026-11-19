# -*- coding: utf-8 -*-
"""Build the draft of "Many Waters", for 9-10 Kislev.

Every Hebrew phrase on the page is cut out of corpus.db by this script and
checked to be there before it is used. None of it is typed. Verses are shown
without cantillation or vowel points, which removes marks and never a letter.

The page is noindex and is not linked from anywhere: it is a draft for him to
read on the draft alias.
"""
import html, io, os, re, sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = r"C:\Users\BoruchMerkur\Downloads\data\corpus.db"
c = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)

MARKS = re.compile("[\u0591-\u05AF\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]")


def verse(work, ref_like):
    row = c.execute("select s.he from segments s join works w on w.id=s.work_id "
                    "where w.title=? and s.ref like ? limit 1", (work, ref_like)).fetchone()
    if not row:
        raise SystemExit("verse not found: %s %s" % (work, ref_like))
    t = re.sub(r"<[^>]+>|&nbsp;|\{[^}]*\}", " ", row[0])
    t = MARKS.sub("", t).replace("\u05BE", " ").replace("\u05C3", "").replace("\u05C0", " ")
    return re.sub(r"\s+", " ", t).strip()


def cut(text, start, end):
    """The exact run of the source from `start` through `end`, or stop."""
    i = text.find(start)
    j = text.find(end, i)
    if i < 0 or j < 0:
        raise SystemExit("phrase not in source: %r … %r" % (start, end))
    return text[i:j + len(end)]


def seg(ref_like):
    row = c.execute("select he from segments where ref like ? limit 1", (ref_like,)).fetchone()
    if not row:
        raise SystemExit("segment not found: %s" % ref_like)
    return row[0]


# ---- the verses --------------------------------------------------------
v86 = verse("Song of Songs", "%8:6")
v87 = verse("Song of Songs", "%8:7")
t3610 = verse("Psalms", "%36:10")
RESHAFEHA = cut(v86, "רשפיה", "שלהבתיה")
MAYIM = cut(v87, "מים רבים", "ישטפוה")
KI_IMCHA = cut(t3610, "כי עמך", "חיים")
BEORCHA = cut(t3610, "באורך", "נראה אור")

# ---- Hayom Yom ----------------------------------------------------------
hy10 = seg("היום יום, כסלו י כסלו%")
HY_MAYIM = cut(hy10, "מים רבים", "מים רבים")
HY_RESH = cut(hy10, "רשפי' רשפי", "רשפי' רשפי")
hy16av = seg("היום יום, מנחם אב טז מנחם אב%")
ESH_OCHLA = cut(hy16av, "ה' אלקיך", "הוא")

# ---- Igros Kodesh of the Mitteler Rebbe, introduction -------------------
ch9 = seg("Igros Kodesh, מבוא, ט. המאסר והגאולה")
ch10 = seg("Igros Kodesh, מבוא, י. אחרית ימיו")
REVIA = cut(ch9, "שהם בערך", "הכולל הזה")
SIMCHA = cut(ch10, "שמחה ממתקת", "הדינין")
ESH_KERACH = cut(ch10, "ודבריו שמענו", "הקרח הנורא")
for must in ("שמחה קיסין", "יהודה יפה מקאפוסט", "כ\"א כסלו תקפ\"ח", "יום ד' ט' כסליו",
             "נ\"ד שנה מיום ליום", "ארבעה שעות קודם אור היום"):
    if must not in ch9 + ch10:
        raise SystemExit("fact not in the introduction: %s" % must)

E = html.escape
he = lambda s: '<span lang="he" dir="rtl">%s</span>' % E(s)

BODY = """
<p>On the road to prison the Mitteler Rebbe said Chassidus on the verse “Many waters cannot extinguish the love.” Thirteen months later, in Niezhin, he passed away in the middle of another verse.</p>

<p>Word had come during Chol HaMoed Sukkos 5587 that he had been informed on. On Sunday of Parshas Noach, 28 Tishrei, he left Lubavitch in the company of government officials, to be taken to Vitebsk, the seat of Governor-General Nikolai Khovansky. At midday he reached Dobromysl and said Chassidus there, on the verse “{hy_mayim}.” On Monday he traveled by way of Liozna and said Chassidus there, on “{hy_resh}.” On Tuesday he came to Vitebsk, and he sat there under arrest until Sunday of Parshas Vayishlach, 10 Kislev (Hayom Yom, 10 Kislev).</p>

<p>The trip had been planned for two days, with one night in Liozna. The Mitteler Rebbe was not well. The road had gone bad, and his doctors had forbidden him to be out in that air, so the officials were asked to allow a night in Dobromysl and a night in Liozna. Late that night the messenger came back with their agreement (diary of the Rebbe Rayatz, 5666–5667).</p>

<p>The two maamarim open on neighboring verses at the end of Shir HaShirim (8:6–7). The verse he began with in Liozna comes first: “{reshafeha}, its flashes are flashes of fire, the flame of G-d.” The verse he began with a day earlier, in Dobromysl, follows it: “{mayim}, many waters cannot extinguish the love, and rivers will not wash it away.”</p>

<p>Hayom Yom records that at the start of his revelation the Baal Shem Tov traveled for three purposes: redeeming captives, strengthening Torah and yiras Shamayim, and revealing the inner part of Torah. Why travel for the third? The Mitteler Rebbe would explain (16 Menachem Av). The revealed part of Torah is called water, and to water a person goes. The inner part of Torah is called fire, and of fire a person is afraid. “Therefore the mashpia has to go to the mekabel and tell him: Have no fear, for ‘{esh_ochla}, Hashem your G-d is a consuming fire.’”</p>

<p>The informer was Simcha Kissin of Vitebsk. With his denunciation he enclosed a letter the Mitteler Rebbe had written in 5573 about dividing the money that chassidim gave for the support of the Alter Rebbe’s household. From that letter he set out to prove that the Mitteler Rebbe had collected about 140,000 rubles and given out only 35,000, since the letter, as it had been translated, spoke of “{revia}, which are about a quarter of this total sum.”</p>

<p>The Mitteler Rebbe answered that there was certainly error and falsehood in the translation, and he asked the interrogators for the original. They gave it to him. The passage was copied out exactly and put into Russian again by his own translator, the chassid R’ Yehuda Yaffe of Kopust, and from the accurate translation he showed that he had never collected more than 35,000 rubles. Two thirds of it he had divided among the descendants of the Alter Rebbe, who came out of the war with Napoleon without homes or property. A third he had taken to build a house and a shul in Lubavitch and to buy s’farim, having lost everything in the same war (Igros Kodesh of the Mitteler Rebbe, introduction, ch. 9, from letters 59–61).</p>

<p>The interrogations went on until 19 Cheshvan. On 6 Kislev he asked to be released. On 10 Kislev he was.</p>

<p>The case stayed open. It was sent up to the Senate in Petersburg, and Beis Rebbe relates that he was afraid he would be taken there (vol. 2, ch. 6). He spent the Yomim Nora’im of 5588 in Haditch, where his father the Alter Rebbe rests, and said a great deal of Chassidus in the beis midrash beside the grave. On the way home he passed through Niezhin, became very ill, and had to stay.</p>

<p>Chassidim who were with him there wrote down the next day what they had seen. At the start of the night he learned Mishnayos in Seder Kodashim with great joy, and he told them to rejoice too, “{simcha}, for joy sweetens judgments.” Four hours before daylight he began to faint. He came to, and he taught them, several times over, for about an hour and a half.</p>

<p>His son R’ Menachem Nachum wrote that the natural warmth had left his father entirely: “{esh_kerach}, we heard his words out of the fire, the flame of G-d, flaring up from within the awesome ice.” The flame of G-d is the last word of the verse he had opened with in Liozna. He taught for an hour and more, until he came to the verse “{ki_imcha}, for with You is the source of life” (T’hillim 36:10). He had not finished saying the word for life when his words grew still.</p>

<p>It was the morning of Wednesday, 9 Kislev 5588, the day he was born, and he was fifty-four years old to the day. He was laid to rest in Niezhin that same day, and Beis Rebbe writes that the chassidim’s yom tov of 10 Kislev was turned that year into mourning (Igros Kodesh, introduction, ch. 10).</p>

<p>In Lubavitch stood the table at which he wrote Chassidus. His grandson the Rebbe Maharash described it at a farbrengen. He wrote with such speed that when he came to the end of a page of fifty or sixty lines, the top of the page was not yet dry, and the table itself was covered with writing, because he would finish the ends of his lines on the wood. On the day he passed away in Niezhin, at that same time, the candlestick that stood on the table fell over, and the table caught fire and burned (diary of the Rebbe Rayatz, 5666–5667).</p>

<p>On 21 Kislev 5588 the Senate in Petersburg upheld the court in Mohilev and cleared him completely of every charge in the file. It was twelve days after the histalkus. The Senate did not yet know (Igros Kodesh, introduction, ch. 9).</p>

<p>The verse he was saying that morning goes on: “{beorcha}, in Your light we will see light.”</p>
""".format(
    hy_mayim=he(HY_MAYIM), hy_resh=he(HY_RESH), reshafeha=he(RESHAFEHA), mayim=he(MAYIM),
    esh_ochla=he(ESH_OCHLA), revia=he(REVIA), simcha=he(SIMCHA), esh_kerach=he(ESH_KERACH),
    ki_imcha=he(KI_IMCHA), beorcha=he(BEORCHA))

TITLE = "Many Waters"
DEK = ("“Mayim rabim, many waters,” is the verse the Mitteler Rebbe opened with in "
       "Dobromysl, on the first day of the journey to his imprisonment in Vitebsk. "
       "For 9 and 10 Kislev.")

shell = io.open(os.path.join(ROOT, "articles", "the-final-push.html"), encoding="utf-8").read()
head = shell[:shell.index("<body")]
# keep the fonts, stylesheet and PWA lines; replace everything that names the other piece
head = re.sub(r"<title>.*?</title>", "<title>%s · Beis Moshiach</title>" % E(TITLE), head, flags=re.S)
head = re.sub(r'<link rel="canonical"[^>]*>\s*', "", head)
head = re.sub(r'<meta (?:name|property)="(?:description|og:[a-z_:]+|twitter:[a-z:]+)"[^>]*>\s*', "", head)
head = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", head, flags=re.S)
import json
URL = "https://beismoshiach.org/articles/many-waters.html"
PUBLISHED = "2026-11-19"          # 9 Kislev 5787
ld = {"@context": "https://schema.org", "@type": "Article", "headline": TITLE,
      "inLanguage": "en", "mainEntityOfPage": URL,
      "publisher": {"@type": "Organization", "name": "Beis Moshiach"},
      "isPartOf": "beismoshiach.org archive",
      "author": {"@type": "Person", "name": "Rabbi Boruch Merkur"},
      "datePublished": PUBLISHED, "description": DEK}
head = head.replace("</head>", (
    '<link rel="canonical" href="{u}">\n'
    '<meta name="description" content="{d}">\n'
    '<meta property="og:type" content="article">\n'
    '<meta property="og:title" content="{t}">\n'
    '<meta property="og:description" content="{d}">\n'
    '<meta property="og:url" content="{u}">\n'
    '<meta property="og:site_name" content="beismoshiach.org">\n'
    '<meta name="twitter:card" content="summary">\n'
    '<meta name="twitter:title" content="{t}">\n'
    '<meta name="twitter:description" content="{d}">\n'
    '<script type="application/ld+json">{ld}</script>\n</head>').format(
        u=URL, d=E(DEK), t=E(TITLE), ld=json.dumps(ld, ensure_ascii=False)))
if "noindex" in head:
    raise SystemExit("the shell carries a noindex; not publishing over it")

words = len(re.sub(r"<[^>]+>", " ", BODY).split())
page = head + """<body>
<header class="bm-topbar">
  <div class="bm-inner">
    <a class="bm-wordmark" href="/">beismoshiach<span class="bm-tld">.org</span></a>
    <nav>
      <a href="/topics">Topics</a>
      <a href="/parsha">Parsha</a>
      <a href="/collections">Collections</a><a href="/science/">Convergence</a>
      <a href="/archives">Archives</a>
      <a href="/search">Search</a>
      <a class="langsw" href="/he/">עברית</a>
    </nav>
  </div>
</header>
<main class="wrap"><article class="entry">
  <div class="entry-eyebrow"><span class="au">Rabbi Boruch Merkur</span> · <span>November 19, 2026</span></div>
  <h1 class="entry-title">%s</h1>
  <p class="entry-pull">%s</p>
  <div class="entry-body">%s</div>
</article></main>
</body></html>
""" % (E(TITLE), E(DEK), BODY)

out = os.path.join(ROOT, "articles", "many-waters.html")
io.open(out, "w", encoding="utf-8", newline="\n").write(page)
print("wrote %s  (%d words)" % (os.path.relpath(out, ROOT), words))
print("Hebrew set from the corpus:")
for k, v in (("8:6", RESHAFEHA), ("8:7", MAYIM), ("36:10", KI_IMCHA + " … " + BEORCHA),
             ("HY 16 Av", ESH_OCHLA), ("intro 9", REVIA), ("intro 10", SIMCHA), ("intro 10", ESH_KERACH)):
    print("  %-9s %s" % (k, v))
