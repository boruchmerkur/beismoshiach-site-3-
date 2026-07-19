// netlify/functions/lily-collect.js
// Same-origin analytics collector. Deploys on EACH site at /api/lily.
//
// The edge function (lily-edge.js) on this same site POSTs its coarse,
// already-anonymized event here — to this site's OWN origin. This collector's
// only job is to relay that coarse count onward, server-to-server, to the
// it receives has no IP and no full user-agent (only path, referrer host,
// country, device class, and a daily-rotating one-way hash). So the only data
// that ever crosses a domain boundary is aggregate, non-identifying counts —
// between the site owner's own two servers.
//
// If you'd rather keep the data on THIS site only (no relay), delete the
// RELAY_URL line and add your own store write instead.

const RELAY_URL = 'https://dreamsitedesign.com/api/lily';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type'
};

const GIF = new Uint8Array([
  71,73,70,56,57,97,1,0,1,0,128,0,0,255,255,255,0,0,0,33,
  249,4,1,0,0,0,0,44,0,0,0,0,1,0,1,0,0,2,2,68,1,0,59
]);
function pixel() {
  return new Response(GIF, { status: 200, headers: { ...CORS, 'Content-Type': 'image/gif', 'Cache-Control': 'no-store' } });
}

export default async (req, context) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405, headers: CORS });

  let payload;
  try { payload = await req.json(); } catch { return new Response('Bad JSON', { status: 400, headers: CORS }); }

  // Forward only the coarse fields — nothing else is accepted or added.
  const coarse = {
    event:   String(payload.event   || 'view').slice(0, 32),
    site:    String(payload.site    || 'unknown').slice(0, 64),
    host:    String(payload.host    || '').slice(0, 128),
    path:    String(payload.path    || '/').slice(0, 200),
    ref:     String(payload.ref     || '').slice(0, 128),
    dev:     String(payload.dev     || '').slice(0, 16),
    country: String(payload.country || '').slice(0, 8),
    vid:     String(payload.vid     || '').slice(0, 32),
    src:     'edge'
  };

  const relay = fetch(RELAY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-lily-relay': '1' },
    body: JSON.stringify(coarse)
  }).catch((e) => { console.error('lily-collect relay failed:', e); });

  if (typeof context?.waitUntil === 'function') context.waitUntil(relay); else await relay;
  return pixel();
};

export const config = { path: '/api/lily' };
