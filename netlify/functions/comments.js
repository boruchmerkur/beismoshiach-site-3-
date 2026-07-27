// Reader comments for beismoshiach.org — v2 Netlify Function.
// Storage is Netlify Blobs (lives in this site's own Netlify account; no third
// party, no tracking). One blob per article slug holds the comment array.
// Comments are HELD FOR APPROVAL: a new comment is stored with pending:true and
// is invisible to visitors until an admin approves it.
//   GET    /api/comments?slug=SLUG          -> { comments: [...] }   (approved only)
//   GET    /api/comments?all=1              -> { items: [...] }      (admin; incl. pending)
//   POST   /api/comments  {slug,name,body}  -> { pending: true }     (held for review)
//   PATCH  /api/comments?slug=SLUG&id=ID     -> { ok }   approve (needs x-admin-key)
//   DELETE /api/comments?slug=SLUG&id=ID     -> { ok }   delete  (needs x-admin-key)
import { getStore } from "@netlify/blobs";

export const config = { path: "/api/comments" };

const MAX_NAME = 60;
const MAX_BODY = 4000;
// keep printable chars + normal whitespace, drop control chars, then trim
const clean = (s) =>
  Array.from(String(s ?? ""))
    .filter((c) => { const n = c.charCodeAt(0); return n >= 32 || n === 9 || n === 10 || n === 13; })
    .join("")
    .trim();
const key = (slug) => "art/" + clean(slug).replace(/[^a-z0-9-]/gi, "").toLowerCase();
const rid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
// what a visitor is allowed to see (no moderation flags)
const publicOf = ({ hidden, pending, ...c }) => c;
const isAdmin = (req) =>
  !!process.env.COMMENTS_ADMIN_KEY && req.headers.get("x-admin-key") === process.env.COMMENTS_ADMIN_KEY;

export default async (req) => {
  const store = getStore({ name: "comments", consistency: "strong" });
  const url = new URL(req.url);

  if (req.method === "GET") {
    // admin: list every article's comments, pending flag intact (moderation view)
    if (url.searchParams.get("all") === "1") {
      if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
      const { blobs } = await store.list({ prefix: "art/" });
      const items = [];
      for (const b of blobs) {
        const list = (await store.get(b.key, { type: "json" })) || [];
        if (list.length) items.push({ slug: b.key.replace(/^art\//, ""), comments: list });
      }
      // articles with pending comments first, then by most recent activity
      const pend = (it) => it.comments.some((c) => c.pending);
      items.sort((a, z) =>
        (pend(z) - pend(a)) ||
        (z.comments[z.comments.length - 1].ts - a.comments[a.comments.length - 1].ts));
      return json({ items });
    }
    // public: approved comments only
    const slug = clean(url.searchParams.get("slug"));
    if (!slug) return json({ comments: [] });
    const list = (await store.get(key(slug), { type: "json" })) || [];
    const visible = list.filter((c) => !c.hidden && !c.pending).map(publicOf);
    return json({ comments: visible });
  }

  if (req.method === "POST") {
    let b;
    try {
      b = await req.json();
    } catch {
      return json({ error: "Malformed request." }, 400);
    }
    if (clean(b.website)) return json({ pending: true }); // honeypot: silently drop bots
    const slug = clean(b.slug);
    const name = clean(b.name).slice(0, MAX_NAME) || "Anonymous";
    const body = clean(b.body).slice(0, MAX_BODY);
    if (!slug || !body) return json({ error: "A comment is required." }, 400);

    const list = (await store.get(key(slug), { type: "json" })) || [];
    // reject an exact duplicate of the most recent comment (double-submit / flood)
    const last = list[list.length - 1];
    if (last && last.body === body && last.name === name) {
      return json({ pending: true }, 200);
    }
    list.push({ id: rid(), name, body, ts: Date.now(), pending: true });
    await store.setJSON(key(slug), list);
    return json({ pending: true }, 201); // held for approval; not shown to visitor
  }

  if (req.method === "PATCH") {
    // approve a pending comment
    if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
    const slug = clean(url.searchParams.get("slug"));
    const id = clean(url.searchParams.get("id"));
    const list = (await store.get(key(slug), { type: "json" })) || [];
    let found = false;
    for (const c of list) if (c.id === id) { delete c.pending; found = true; }
    if (found) await store.setJSON(key(slug), list);
    return json({ ok: found });
  }

  if (req.method === "DELETE") {
    if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
    const slug = clean(url.searchParams.get("slug"));
    const id = clean(url.searchParams.get("id"));
    const list = (await store.get(key(slug), { type: "json" })) || [];
    const next = list.filter((c) => c.id !== id);
    await store.setJSON(key(slug), next);
    return json({ ok: true, remaining: next.length });
  }

  return json({ error: "Method not allowed." }, 405);
};
