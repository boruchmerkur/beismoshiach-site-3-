// netlify/edge-functions/lily-edge.js
// First-party edge analytics — privacy-clean rewrite.
//
// Design rules this file follows (so it's safe to ship on any site):
//   1. SAME-ORIGIN. It POSTs to /api/lily on THIS site's own origin — never
//      to another domain. Nothing about the visitor leaves the origin they
//      are already talking to. (The site's /api/lily collector may relay
//      COARSE, already-anonymized counts onward to a central dashboard
//      server-to-server — see lily-collect.js — but that hop carries no raw
//      IP and no full user-agent.)
//   2. DOESN'T TOUCH THE PAGE. It never reads or rewrites the response body.
//      The HTML the visitor receives is byte-for-byte what the origin served
//      — no injected tags, no reconstruction. We only look at request headers
//      and the response's status/content-type.
//   3. COARSE, NOT RAW. It forwards path, referrer HOST (not full URL),
//      country, and a device class. The raw IP and full UA never leave this
//      function: the IP is folded into a daily-rotating one-way hash here at
//      the edge (for approximate unique counts) and then discarded; the UA is
//      used only in-memory for bot filtering + device class.
//   4. DISCLOSED. Each site carries a visible "Analytics" note in its footer
//
//   Install: drop at netlify/edge-functions/lily-edge.js
//   Optional env: LILY_SITE=<short-name>, LILY_IGNORE_IPS=<csv> (self-exclude)

const BOT_RE = /\bbot\b|crawl|spider|slurp|bingpreview|facebookexternalhit|whatsapp|telegram|slackbot|discordbot|twitterbot|linkedinbot|google-inspectiontool|pagespeed|lighthouse|headlesschrome|phantomjs|puppeteer|playwright|chrome-lighthouse|gptbot|claudebot|anthropic|perplexity|ahrefs|semrush|mj12bot|dotbot|petalbot|yandex|baiduspider|applebot|duckduckbot|sogou|exabot|ia_archiver|archive\.org|monitis|uptimerobot|pingdom|statuscake|hetrix|dataprovider|netcraft|dataforseo/i;

function detectDevice(ua) {
  if (!ua) return '';
  if (/iPad|Tablet|PlayBook|Silk/i.test(ua)) return 'tablet';
  if (/Android/i.test(ua) && !/Mobile/i.test(ua)) return 'tablet';
  if (/Mobi|iPhone|iPod|Android.*Mobile|Windows Phone|BlackBerry|Opera Mini|IEMobile/i.test(ua)) return 'mobile';
  return 'desktop';
}

// Daily-rotating, one-way visitor hash. Because the day is part of the input
// the value is useless for tracking anyone across days, and the raw IP is
// never stored or forwarded — only this digest is. This is how Plausible /
// Fathom count uniques without cookies.
async function dailyVid(day, ip, ua, site) {
  try {
    const buf = await crypto.subtle.digest(
      'SHA-256', new TextEncoder().encode(day + '|' + ip + '|' + ua + '|' + site)
    );
    return [...new Uint8Array(buf)].slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');
  } catch { return ''; }
}

// An entry ending in '.' or ':' matches as a PREFIX, so a residential lease
// that moves inside its own block (99.229.90.241 -> 99.229.88.7) stays
// excluded. Exact-match lists fail silently: the address changes, the list
// stops matching, and nothing anywhere reports that it stopped working.
function ipExcluded(ip, list) {
  if (!ip) return false;
  for (const entry of list) {
    if (entry.endsWith('.') || entry.endsWith(':')) {
      if (ip.startsWith(entry)) return true;
    } else if (ip === entry) return true;
  }
  return false;
}

// Shown once, when someone toggles their own device in or out. Deliberately
// self-contained: no stylesheet, no font, no image, so it renders identically
// on every site this function is installed on.
function optOutPage(off, host) {
  const title = off ? 'This device is not counted' : 'This device is counted';
  const body = off
    ? 'Page views from this browser will no longer appear in analytics for '
      + host + '.'
    : 'Page views from this browser are being counted again.';
  const note = off
    ? 'The setting is a cookie on this device only. Clearing cookies undoes '
      + 'it, and every other browser or phone you use needs its own visit to '
      + 'this address.'
    : 'Visit this address with ?lily=off to stop counting this device.';
  return '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<title>' + title + '</title><style>'
    + 'body{margin:0;min-height:100vh;display:grid;place-items:center;'
    + 'background:#12232b;color:#eef2f3;'
    + 'font:16px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}'
    + 'main{max-width:34rem;padding:2rem}'
    + 'h1{font-size:1.35rem;margin:0 0 .75rem;letter-spacing:-.01em}'
    + 'p{margin:0 0 1rem}small{color:#93a7ae;display:block;margin-top:1.5rem}'
    + 'code{background:#ffffff14;padding:.1em .4em;border-radius:3px}'
    + '</style></head><body><main><h1>' + title + '</h1><p>' + body + '</p>'
    + '<small>' + note + '</small></main></body></html>';
}

export default async (req, context) => {
  const url = new URL(req.url);
  const path = url.pathname;

  // Device-level opt-out, for the people who build these sites. An IP list is
  // the wrong instrument: leases rotate, phones sit behind carrier NAT, and a
  // stale list reports nothing — your own traffic just quietly reappears in
  // the numbers. A cookie is pinned to the device and cannot drift.
  //   /?lily=off  -> this browser is never counted here again
  //   /?lily=on   -> count it again
  const lilyToggle = url.searchParams.get('lily');
  if (lilyToggle === 'off' || lilyToggle === 'on') {
    const off = lilyToggle === 'off';
    return new Response(optOutPage(off, url.hostname), {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
        'set-cookie': 'lily_off=' + (off ? '1' : '') + '; Path=/; Max-Age='
          + (off ? 63072000 : 0) + '; SameSite=Lax; Secure',
      },
    });
  }
  // Returning nothing hands the request straight back to the origin with this
  // function taking no further part — the opted-out visitor is served exactly
  // as if the tracker were not installed.
  if (/(?:^|;\s*)lily_off=1(?:\s*;|$)/.test(req.headers.get('cookie') || '')) return;


  // Skip API/admin/asset paths (excludedPath below also covers most).
  if (
    path.startsWith('/api/') || path.startsWith('/.netlify/') ||
    /\.(?:js|css|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|otf|map|json|xml|txt|pdf|mp4|webm|mp3|zip)$/i.test(path)
  ) return;

  // Skip browser prefetch/prerender — the visitor never actually saw it.
  const secPurpose = req.headers.get('sec-purpose') || '';
  const legacyPurpose = req.headers.get('purpose') || '';
  if (/prefetch|prerender/i.test(secPurpose) || /prefetch/i.test(legacyPurpose)) return;

  // Let the origin serve the page. We inspect status + content-type only —
  // the body is never read, and this exact response object is returned
  // untouched, so the visitor gets byte-for-byte what the origin sent.
  const response = await context.next();
  const ct = response.headers.get('content-type') || '';
  if (!ct.includes('text/html') || response.status >= 400) return response;

  const ua = req.headers.get('user-agent') || '';
  if (ua && BOT_RE.test(ua)) return response;  // UA used here only, never sent

  // Raw IP used here only (self-exclusion + hashing), then discarded.
  const ip = context.ip || '';
  // Both variable names are honoured. The install doc has always documented
  // IGNORE_IPS while this file read LILY_IGNORE_IPS, so a site that set either
  // one meant it — and that mismatch is why the owner's own visits were being
  // counted on every site for months without the dashboard ever saying so.
  const ignore = [Netlify.env.get('LILY_IGNORE_IPS'), Netlify.env.get('IGNORE_IPS')]
    .join(',').split(/[\s,]+/).filter(Boolean);
  if (ipExcluded(ip, ignore)) return response;

  const site = (Netlify.env.get('LILY_SITE') || '').trim() || url.hostname.split('.')[0] || 'unknown';

  /* Browser-signal gate. OFF unless a site is named in LILY_STRICT_SITES, so
     no other site's numbers move by so much as one view.

     Why this site needs it: 95% of its views land on /articles spread over
     12,257 distinct paths, the top ten pages are 3.5% of the total, 98.8% of
     requests carry no referrer, 91% are desktop, and the country tail runs
     through Singapore, Vietnam and Bangladesh. Nobody types deep archive URLs.
     That is a fleet of scrapers reading twenty years of back issues, and
     because they never say "bot" in the user-agent, BOT_RE above waves every
     one of them through.

     What is checked is what a browser sends and a scraper usually does not.
     Absence of Sec-Fetch-* is NOT held against anyone — older Safari omits it
     — so only a header that actively contradicts a page view counts. Erring
     toward counting is deliberate: a missed crawler is a number slightly too
     high, while a wrongly-dropped reader is a person who does not exist in the
     record at all, and there is no way to notice that has happened. */
  const strict = new Set((Netlify.env.get('LILY_STRICT_SITES') || '')
    .split(/[\s,]+/).filter(Boolean));
  if (strict.has(site)) {
    const hdr = (n) => req.headers.get(n) || '';
    let why = '';
    // Every real browser states a language preference. Very few scrapers do.
    if (!hdr('accept-language')) why = 'no-accept-language';
    else {
      // A page view accepts HTML. Text harvesters usually send */* and nothing else.
      const acc = hdr('accept');
      if (acc && !/text\/html|application\/xhtml/i.test(acc)) why = 'accept-not-html';
      // Present-but-wrong Sec-Fetch-* means this was not a top-level navigation.
      else if (hdr('sec-fetch-mode') && hdr('sec-fetch-mode') !== 'navigate') why = 'mode=' + hdr('sec-fetch-mode');
      else if (hdr('sec-fetch-dest') && hdr('sec-fetch-dest') !== 'document') why = 'dest=' + hdr('sec-fetch-dest');
    }
    if (why) {
      // Logged, not silent: the count is visible in the Netlify function log,
      // so how much this is removing can be checked rather than assumed.
      console.log('lily-edge filtered [' + why + '] ' + url.pathname.slice(0, 120));
      return response;
    }
  }

  const day = new Date().toISOString().slice(0, 10);

  // Referrer reduced to hostname; same-origin referrers dropped.
  let refHost = '';
  const rawRef = req.headers.get('referer') || '';
  if (rawRef) { try { const h = new URL(rawRef).hostname; if (h && h !== url.hostname) refHost = h; } catch {} }

  const event = {
    event: 'view',
    site,
    host: url.hostname,
    path: url.pathname + url.search,
    ref: refHost,                                  // host only, no full URL
    dev: detectDevice(ua),                          // class only, no UA
    country: context.geo?.country?.code || '',
    vid: await dailyVid(day, ip, ua, site),         // hashed here; IP not sent
    src: 'edge'
  };

  // Fire-and-forget to THIS site's own origin. A same-origin collector
  // (/api/lily) writes/relays it; the visitor doesn't wait on this. The
  // x-lily-relay header marks this as a pre-hashed, coarse event so the
  // receiver trusts its fields as-is (works whether /api/lily is a relaying
  // collector or, on the dashboard's own site, the central ingest directly).
  const fire = fetch(url.origin + '/api/lily', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-lily-relay': '1' },
    body: JSON.stringify(event)
  }).catch((e) => { console.error('lily-edge beacon failed:', e); });
  if (typeof context.waitUntil === 'function') context.waitUntil(fire);

  return response; // untouched
};

export const config = {
  path: '/*',
  excludedPath: [
    '/api/*', '/.netlify/*', '/assets/*', '/static/*',
    '/*.js', '/*.css', '/*.png', '/*.jpg', '/*.jpeg', '/*.gif',
    '/*.svg', '/*.webp', '/*.ico', '/*.woff', '/*.woff2', '/*.ttf', '/*.otf',
    '/*.json', '/*.xml', '/*.txt', '/*.map', '/*.pdf', '/*.mp4', '/*.webm', '/*.mp3', '/*.zip'
  ]
};
