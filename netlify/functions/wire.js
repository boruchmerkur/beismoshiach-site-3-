// The wire for beismoshiach.org/science/ — v2 Netlify Function.
//
// Ported from the standalone Convergence site. Every line below the entry point
// is carried over unchanged: the feeds (fifteen of them now), the relevance gate,
// the image
// upgrade chain, the near-duplicate collapse. Only the handler shape is new.
//
// THIS IS A v2 FUNCTION and claims /api/wire through its own inline `config`.
// Do NOT add a redirect for it in netlify.toml. A v2 function with a custom
// path is not served at /.netlify/functions/wire, so a redirect pointing there
// rewrites every request to a dead URL — that is exactly what took /api/lily
// down on this site for three months. The note in netlify.toml says the same.
//
//   GET /api/wire            -> normalised, deduped, sorted items
//   GET /api/wire?health=1   -> per-feed status, incl. what was rejected
export const config = { path: "/api/wire" };

const FEEDS = [
  { u: 'https://phys.org/rss-feed/',                        n: 'Phys.org',          l: 'science' },
  { u: 'https://www.quantamagazine.org/feed/',              n: 'Quanta',            l: 'science' },
  { u: 'https://www.sciencedaily.com/rss/top/science.xml',  n: 'ScienceDaily',      l: 'science' },
  { u: 'https://www.livescience.com/feeds/all',             n: 'Live Science',      l: 'science' },
  { u: 'https://www.newscientist.com/feed/home/',           n: 'New Scientist',     l: 'science' },
  { u: 'https://www.nasa.gov/feed/',                        n: 'NASA',              l: 'science' },
  { u: 'https://www.sciencenews.org/feed',                  n: 'Science News',      l: 'science' },
  { u: 'https://arstechnica.com/science/feed/',             n: 'Ars Technica',      l: 'science' },
  { u: 'https://moshiach101.blogspot.com/feeds/posts/default?alt=rss', n: 'Moshiach 101', l: 'torah' },
  { u: 'https://anash.org/feed/',                           n: 'Anash.org',         l: 'torah' },
  { u: 'https://collive.com/feed/',                         n: 'COLlive',           l: 'torah' },
  { u: 'https://www.crownheights.info/feed/',               n: 'CrownHeights.info', l: 'torah' },
  { u: 'https://www.chabad.org/tools/rss/magazine_rss.xml', n: 'Chabad.org Magazine', l: 'torah' }
  // Held back on purpose — see DEPLOY.md:
  // https://www.nature.com/nature.rss            live, but journal TOC: no images, DOI-heavy
  // https://www.chabad.org/tools/rss/news_rss.xml live, but empty descriptions and stale
];

const READINGS = [
  { k:'daas', art:'/art/daas.webp', pos:'50% 60%', h:'וּמָלְאָה הָאָרֶץ דֵּעָה', c:'Yeshayahu 11:9',
    why:'Knowledge becoming ordinary rather than rare is the precondition the verse describes.',
    rx:/(artificial intelligence|language model|machine learning|translat|archive|open access|dataset|literac|educat|knowledge|library|search engine)/i },
  { k:'techiya', art:'/art/techiya.webp', pos:'50% 55%', h:'הִנֵּה אֲנִי פֹתֵחַ אֶת קִבְרוֹתֵיכֶם', c:'Yechezkel 37:12',
    why:'Biological decline treated as reversible rather than one-directional.',
    rx:/(stem cell|regenerat|reprogram|longevity|lifespan|aging|ageing|senescen|tissue|organoid|transplant|cryo|DNA repair|gene therapy|CRISPR)/i },
  { k:'echad', art:'/art/echad.webp', pos:'50% 50%', h:'ה׳ אֶחָד', c:'Devarim 6:4',
    why:'Physics moving toward fewer laws, not more.',
    rx:/(unified|unification|grand unif|quantum gravity|standard model|symmetr|fundamental force|theory of everything|entangl)/i },
  { k:'shefa', art:'/art/shefa.webp', pos:'50% 55%', h:'לֹא רָעָב וְלֹא מִלְחָמָה', c:'Rambam 12:5',
    why:'Scarcity turning into a distribution problem rather than a production one.',
    rx:/(crop yield|harvest|\bcrops?\b|fusion|solar|battery|desalinat|famine|food secur|abundance|fertili[sz]er|manufactur|vaccine|malaria|drought)/i },
  { k:'bereishis', art:'/art/bereishis.webp', pos:'50% 45%', h:'בְּרֵאשִׁית בָּרָא', c:'Bereishis 1:1',
    why:'A universe with a finite past — for most of the history of science, the unpopular position.',
    rx:/(cosmolog|big bang|early universe|telescope|JWST|Webb|galax|cosmic|dark energy|dark matter|exoplanet|black hole)/i },
  { k:'geula', art:'/art/plate.webp', pos:'50% 50%', h:'וְכִתְּתוּ חַרְבוֹתָם לְאִתִּים', c:'Yeshayahu 2:4',
    why:'The sources put an end to war in the same paragraph as an end to want.',
    rx:/(moshiach|mashiach|geula|redemption|Rebbe|Beis Hamikdash|third temple|ceasefire|peace (deal|treaty|accord)|disarm)/i }
];
const readingFor = t => READINGS.find(r => r.rx.test(t)) || null;

// Broader subjects, used only when a story matches none of the six readings.
// A key is honoured only if its file is actually in art/ — see ART_ON_DISK.
const TOPICS = [
  { k:'lab',     art:'/art/topic-lab.webp',     pos:'50% 50%',
    rx:/(cell|protein|enzyme|genome|gene|bacteri|virus|antibod|trial|patient|clinic|drug|vaccine|microscop|lab\b|biolog|neuro|immun)/i },
  { k:'earth',   art:'/art/topic-earth.webp',   pos:'50% 55%',
    rx:/(climate|ocean|glacier|ice sheet|volcan|earthquake|geolog|atmospher|weather|coral|forest|species|ecosystem|carbon|emissions)/i },
  { k:'compute', art:'/art/topic-compute.webp', pos:'50% 50%',
    rx:/(algorithm|comput|processor|chip|semiconductor|software|data\b|model|quantum comput|robot|encryption|network)/i },
  { k:'dig',     art:'/art/topic-dig.webp',     pos:'50% 55%',
    rx:/(archaeolog|excavat|manuscript|inscription|ancient|artifact|scroll|tablet|ruins|dig\b|antiquit|historian)/i },
  { k:'kehilla', art:'/art/topic-kehilla.webp', pos:'50% 50%',
    rx:/(shliach|shluchim|chabad house|community|kehilla|yeshiva|shul|synagogue|farbrengen|mikvah|school|campus|dinner|gathering)/i },
  { k:'eretz',   art:'/art/topic-eretz.webp',   pos:'50% 55%',
    rx:/(israel|jerusalem|yerushalayim|tel aviv|hebron|tzfat|negev|galilee|the land|aliyah)/i }
];

// Only these have files on disk. Add a key here when you drop its webp into art/;
// until then its stories fall to the one-line list instead of showing nothing.
const ART_ON_DISK = new Set(['zohar','daas','echad','techiya','shefa','bereishis','geula']);

// Plates belong to Points of Convergence and The Column. A wire card shows a real
// photograph from the feed or it shows nothing and drops to the one-line list —
// otherwise every story matching the same reading gets the same picture, and that
// picture is already on the page further down.
function plateFor() { return { art: '', pos: '' }; }



const decode = s => (s || '')
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
  .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
  .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
  .replace(/&(amp|lt|gt|quot|apos|nbsp|#8217|#8216|#8220|#8221|#8230);/g, m => ({
    '&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'",'&nbsp;':' ',
    '&#8217;':'\u2019','&#8216;':'\u2018','&#8220;':'\u201C','&#8221;':'\u201D','&#8230;':'\u2026'
  }[m] || m));

const tagOf = (block, tag) => {
  const m = new RegExp('<' + tag + '(?:\\s[^>]*)?>([\\s\\S]*?)<\\/' + tag + '>', 'i').exec(block);
  return m ? decode(m[1]).trim() : '';
};
const attrOf = (block, tag, attr) => {
  const m = new RegExp('<' + tag + '\\b[^>]*\\b' + attr + '=["\']([^"\']+)["\']', 'i').exec(block);
  return m ? decode(m[1]) : '';
};
const plain = s => decode(s).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

// --- images -------------------------------------------------------------
// Feeds hand over whatever size they feel like, often a 150px thumbnail.
// Collect every candidate, upgrade the URL to the largest version the host
// will serve, then keep the biggest. Anything still tiny is dropped rather
// than blown up into mush.

function upgrade(u) {
  if (!u) return { url: '', freed: false };
  const before = decode(u).trim();
  let s = before.replace(/^http:\/\//, 'https://');

  // WordPress generated crops:  photo-1024x683.jpg -> photo.jpg
  s = s.replace(/-\d{2,4}x\d{2,4}(\.(?:jpe?g|png|webp|gif|avif))(?=$|\?)/i, '$1');

  // Jetpack / Photon / WP resize params
  s = s.replace(/([?&])(?:w|h|width|height|resize|fit|crop|quality|q|ssl)=[^&]*/gi, '$1')
       .replace(/[?&]+$/, '').replace(/\?&+/, '?').replace(/&{2,}/g, '&');

  // Future plc CDN (Live Science, New Scientist) serves full size bare
  if (/futurecdn\.net/i.test(s)) s = s.split('?')[0];

  // Phys.org / Science X. The feed only ever offers the 90px square under
  // /csz/news/tmb/; the same filename under /csz/news/800a/ is the 800px
  // version the article page itself uses. Without this every Phys.org story
  // fails the 400px floor and drops to the one-line list.
  s = s.replace(/\/csz\/news\/tmb\//, '/csz/news/800a/');

  // Blogger / Google user content size tokens
  s = s.replace(/\/s\d{2,4}(-c)?\//, '/s1600/')
       .replace(/\/w\d+-h\d+(-[a-z-]+)?\//, '/s1600/')
       .replace(/=s\d{2,4}(-c)?$/, '=s1600')
       .replace(/=w\d+-h\d+(-[a-z-]+)?$/, '=s1600');

  // freed == we stripped or raised a size token, so any width the feed
  // declared describes the old thumbnail, not the URL we're now asking for.
  return { url: s, freed: s !== before.replace(/^http:\/\//, 'https://') };
}

const THUMB = /(^|[^0-9])(?:\/|_|-)(?:50|60|72|75|96|100|120|150|160|180|200)x?(?:50|60|72|75|96|100|120|150|160|180|200)?(?:\/|_|-|\.)/;

function scoreOf(url, w, h, freed) {
  let n = 0;
  if (w && !freed) n = w;
  else if (/\/s1600\//.test(url)) n = 1200;
  else if (/futurecdn|arstechnica|scx[12]|quantamagazine/i.test(url)) n = 900;
  else n = 600;                                  // unknown: assume usable
  if (THUMB.test(url)) n = Math.min(n, 180);     // clearly a thumbnail path
  if (/\.svg($|\?)|spacer|logo|avatar|icon|feedburner|gravatar|pixel|1x1/i.test(url)) n = 0;
  if (h && w && w / h > 4) n = 0;                // banner strip, not a photo
  return n;
}

function imageIn(block) {
  const cands = [];
  const push = (u, w, h) => {
    const { url, freed } = upgrade(u);
    if (!url || !/^https:\/\//.test(url)) return;
    cands.push({ url, raw: decode(u).trim(), score: scoreOf(url, +w || 0, +h || 0, freed) });
  };

  const re = /<(media:content|media:thumbnail|enclosure)\b([^>]*)>/gi;
  let m;
  while ((m = re.exec(block))) {
    const attrs = m[2];
    const url = (/\burl=["']([^"']+)["']/i.exec(attrs) || [])[1];
    const type = (/\btype=["']([^"']+)["']/i.exec(attrs) || [])[1] || '';
    if (!url) continue;
    if (type && !/^image\//i.test(type)) continue;
    push(url,
      (/\bwidth=["']?(\d+)/i.exec(attrs) || [])[1],
      (/\bheight=["']?(\d+)/i.exec(attrs) || [])[1]);
  }

  const html = decode(block);
  const imgRe = /<img\b([^>]*)>/gi;
  while ((m = imgRe.exec(html))) {
    const attrs = m[1];
    const src = (/\bsrc=["']([^"']+)["']/i.exec(attrs) || [])[1];
    if (src) push(src,
      (/\bwidth=["']?(\d+)/i.exec(attrs) || [])[1],
      (/\bheight=["']?(\d+)/i.exec(attrs) || [])[1]);
    // srcset: take the widest entry
    const ss = (/\bsrcset=["']([^"']+)["']/i.exec(attrs) || [])[1];
    if (ss) ss.split(',').forEach(part => {
      const bits = part.trim().split(/\s+/);
      if (bits[0]) push(bits[0], (/(\d+)w/.exec(bits[1] || '') || [])[1]);
    });
  }

  cands.sort((a, b) => b.score - a.score);
  const best = cands[0];
  if (!best || best.score < 400) return { img: '', imgRaw: '' };  // too small to show
  return { img: best.url, imgRaw: best.raw };
}

// Many feeds glue the photo credit onto the front of the description
// ("Kevin Frayer/Getty Images It is said that…"). Cut it before it reaches a card.
const CREDIT_AGENCIES = 'Getty Images|Getty|Reuters|AFP|AP Photo|Associated Press|Shutterstock|Alamy|iStock|Unsplash|NASA|ESA|JAXA|SPL|Science Photo Library|Bloomberg|EPA|AAP';
function stripCredit(t) {
  if (!t) return '';
  let s = t.trim();
  // "Someone Name/Getty Images" or "Agency/Agency" at the very start
  s = s.replace(new RegExp('^[^.!?]{0,70}?\\/(?:' + CREDIT_AGENCIES + ')\\b[\\s\\u2014\\u2013:;,.-]*', 'i'), '');
  // "Credit: …" / "Photo: …" / "Image: …" / "Photograph: …" up to the first sentence end
  s = s.replace(/^(?:photo|photograph|image|picture|credit|source|illustration)\s*(?:by|:)\s*[^.!?]{0,80}?[.!?—–]\s*/i, '');
  // agency on the LEFT of the slash: "NASA/JPL-Caltech", "ESA/Hubble"
  s = s.replace(new RegExp('^(?:' + CREDIT_AGENCIES + ')\\/[A-Za-z][A-Za-z.-]*\\b[\\s\\u2014\\u2013:;,.-]*', 'i'), '');
  // a bare agency name alone at the front
  s = s.replace(new RegExp('^(?:' + CREDIT_AGENCIES + ')\\b[\\s\\u2014\\u2013:;,.-]+', 'i'), '');
  return s.trim();
}

// --- relevance gate ---------------------------------------------------------
// Sourcing is not the same as relevance. The Chabad and Geula outlets are general
// community papers: they carry a Torah-and-science piece perhaps once a month and
// mikvah openings every day. So a story from those feeds is admitted ONLY if it
// engages science hard — soft words like "study", "professor" or "data" are not
// enough, because a community paper uses them about anything. The science press is
// admitted by default, minus the press-release and personnel filler that every
// institutional feed carries.

// Strict: concrete science, required for anything from a general-interest feed.
const HARD_SCIENCE = new RegExp([
  'physic|quantum|particle|relativity|thermodynam','chemis|molecul|isotope|catalys',
  'biolog|genome|genetic|\\bDNA\\b|\\bRNA\\b|protein|enzyme|neuron|stem cell|microb|bacteri|virus',
  'astronom|astrophys|cosmolog|telescope|galax|nebula|exoplanet|black hole|spacecraft|orbit',
  'geolog|seismic|volcan|glacier|fossil|archaeolog|excavat',
  'climate|atmospher|ocean(ograph)?|ecosystem|biodivers',
  'medicine|medical|clinical trial|vaccine|pathogen|diagnos',
  'mathematic|theorem|equation|algorithm|topolog',
  'artificial intelligence|machine learning|semiconductor|robotics|nanotech',
  'fusion|fission|reactor|photovolta|superconduct',
  'laboratory|peer.reviewed|scientific (study|paper|journal)|\\bNobel Prize\\b',
  'science and torah|torah and science|moshiach (and|&) science|faith and science'
].join('|'), 'i');

// Things institutional feeds publish that are not findings.
// Every term is anchored with . Without the leading boundary 'appoint' also
// matched 'disappointing'; without the trailing one 'gala' matched 'galaxy' and
// 'galaxies', which silently rejected most of the cosmology stories the
// bereishis reading exists to catch. Anchor anything added here the same way.
const NOT_A_FINDING = new RegExp([
  '\\bpodcast','\\bwatch live|\\blivestream|\\blive coverage','\\bwebinar',
  '\\binternship|\\bfellowship application',
  '\\bnow streaming|\\bdebuts on|\\bcoming soon to','\\bback to school|\\bnew school year',
  '\\bobituar|\\bpasses away|\\bmourns|\\bremembering|\\blevaya|\\bshiva\\b',
  '\\bprofile of|\\bmeet the',
  '\\bappoint|\\bnames new|\\bjoins as|\\bpromoted to|\\bsteps down',
  '\\baward ceremony|\\bgala\\b|\\bbanquet|\\bdinner honou?ring',
  '\\bsubscribe|\\bnewsletter|\\bsign up','\\bphotos? of the week|\\bimage of the day|\\bphoto essay',
  '\\bjob opening|\\bwe.re hiring',
  // 'birth of' alone rejected 'the birth of the universe' and 'the birth of
  // stars', so it is scoped to the announcements it was written for.
  '\\bwedding|\\bengagement\\b|\\bmazal tov|\\bbirth of (?:a |our |their )?(?:son|daughter|baby|boy|girl|twins)'
].join('|'), 'i');

// A headline that is only a person's name is a profile, not a finding.
const NAME_ONLY = /^[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+$/;

function admits(title, sum, lane) {
  const head = title + ' ' + String(sum || '').slice(0, 160);
  if (NOT_A_FINDING.test(head)) return false;
  if (NAME_ONLY.test(title.trim())) return false;
  if (lane === 'torah') return HARD_SCIENCE.test(title + ' ' + sum);
  return true;
}

function parse(xml, feed, stats) {
  const blocks = xml.match(/<(item|entry)\b[\s\S]*?<\/\1>/gi) || [];
  const out = [];
  for (const b of blocks.slice(0, 24)) {
    const title = plain(tagOf(b, 'title'));
    let link = tagOf(b, 'link') || attrOf(b, 'link', 'href');
    link = (link || '').trim();
    if (!title || !link) continue;
    const body = tagOf(b, 'content:encoded') || tagOf(b, 'description') || tagOf(b, 'summary') || tagOf(b, 'content');
    const sum = stripCredit(plain(body)).slice(0, 420);
    const dateRaw = tagOf(b, 'pubDate') || tagOf(b, 'published') || tagOf(b, 'updated') || tagOf(b, 'dc:date');
    const ts = dateRaw ? Date.parse(dateRaw) : NaN;
    if (!admits(title, sum, feed.l)) {
      if (stats) { stats.rejected++; if (stats.samples.length < 4) stats.samples.push(title.slice(0, 70)) }
      continue;
    }
    const r = readingFor(title + ' ' + sum);
    const pl = plateFor(title + ' ' + sum, r);
    const pic = imageIn(b);
    out.push({
      title, link, sum, img: pic.img, imgRaw: pic.imgRaw,
      ts: isNaN(ts) ? 0 : ts, src: feed.n, lane: feed.l,
      read: r ? { h: r.h, c: r.c, why: r.why } : null,
      plate: pl.art, platePos: pl.pos
    });
  }
  return out;
}

async function grab(feed) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 8000);
  try {
    const res = await fetch(feed.u, {
      signal: ctl.signal,
      headers: { 'User-Agent': 'ConvergenceWire/1.0 (+https://convergence.example)', 'Accept': 'application/rss+xml, application/xml, text/xml, */*' }
    });
    if (!res.ok) return { feed, ok: false, why: 'HTTP ' + res.status, items: [] };
    const xml = await res.text();
    const stats = { rejected: 0, samples: [] };
    const items = parse(xml, feed, stats);
    return {
      feed, ok: items.length > 0,
      why: items.length ? '' : (stats.rejected ? 'all ' + stats.rejected + ' items failed the relevance gate' : 'parsed 0 items'),
      items, rejected: stats.rejected, rejectedSamples: stats.samples,
      withImages: items.filter(i => i.img).length,
      newest: items.reduce((a, i) => Math.max(a, i.ts), 0)
    };
  } catch (e) {
    return { feed, ok: false, why: e.name === 'AbortError' ? 'timeout' : String(e.message || e), items: [] };
  } finally { clearTimeout(timer); }
}

// --- near-duplicate detection ------------------------------------------------
// Outlets run the same press release under reworded headlines, and the same photo
// off different CDNs. Exact-string matching misses both, so compare shapes.

const STOP = new Set(('a an the of in on at to for from with by and or as is are was were '
  + 'new study finds found say says said research researchers scientists report reports how why '
  + 'this that it its their could can may might').split(' '));

function shingle(title) {
  return new Set(String(title).toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ').split(/\s+/)
    .filter(w => w.length > 2 && !STOP.has(w)));
}
function overlap(a, b) {
  if (!a.size || !b.size) return 0;
  let hit = 0;
  for (const w of a) if (b.has(w)) hit++;
  return hit / Math.min(a.size, b.size);   // containment, so a longer rewrite still matches
}
// Two pictures are the same picture if the file at the end of the path is the same.
function imageKey(url) {
  const clean = String(url).split('?')[0].toLowerCase();
  const file = clean.split('/').pop();
  return (file && file.length > 6) ? file : clean;
}

export default async (req) => {
  const health = new URL(req.url).searchParams.get('health');
  const results = await Promise.all(FEEDS.map(grab));

  if (health) {
    return new Response(JSON.stringify({
        checked: new Date().toISOString(),
        feeds: results.map(r => ({
          source: r.feed.n, lane: r.feed.l, url: r.feed.u,
          ok: r.ok, note: r.why,
          items: r.items.length,
          rejectedAsOffTopic: r.rejected || 0,
          rejectedExamples: r.rejectedSamples || [],
          withImages: r.withImages || 0,
          newest: r.newest ? new Date(r.newest).toISOString() : null
        }))
      }, null, 2), {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
    });
  }

  const items = [];
  const shapes = [];
  let sameStory = 0;
  for (const r of results) for (const it of r.items) {
    const sh = shingle(it.title);
    if (shapes.some(prev => overlap(sh, prev) >= 0.6)) { sameStory++; continue; }
    shapes.push(sh); items.push(it);
  }
  items.sort((a, b) => b.ts - a.ts);

  // No picture may appear twice. Syndicated stories share artwork, and some feeds
  // reuse one house image across every item. First story to claim a URL keeps it;
  // the rest lose their picture and fall to the one-line list.
  const claimed = new Set();
  let dropped = 0;
  for (const it of items) {
    if (!it.img) continue;
    const key = imageKey(it.img);
    if (claimed.has(key)) { it.img = ''; it.imgRaw = ''; dropped++; }
    else claimed.add(key);
  }

  return new Response(JSON.stringify({
      pulled: new Date().toISOString(),
      duplicateImagesDropped: dropped,
      sameStoryDropped: sameStory,
      responding: results.filter(r => r.ok).length,
      total: FEEDS.length,
      quiet: results.filter(r => !r.ok).map(r => r.feed.n),
      items
    }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=0, s-maxage=900, stale-while-revalidate=3600'
    }
  });
};
