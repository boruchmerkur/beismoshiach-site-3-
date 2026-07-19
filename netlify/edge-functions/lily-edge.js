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

export default async (req, context) => {
  const url = new URL(req.url);
  const path = url.pathname;

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
  const ignore = (Netlify.env.get('LILY_IGNORE_IPS') || '').split(/[\s,]+/).filter(Boolean);
  if (ip && ignore.includes(ip)) return response;

  const site = (Netlify.env.get('LILY_SITE') || '').trim() || url.hostname.split('.')[0] || 'unknown';
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
