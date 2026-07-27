// Reader comments for beismoshiach.org — v2 Netlify Function.
// Storage is Netlify Blobs (lives in this site's own Netlify account; no third
// party, no tracking). One blob per article slug holds the comment array.
//   GET    /api/comments?slug=SLUG          -> { comments: [...] }
//   POST   /api/comments  {slug,name,body}  -> { comment: {...} }   (appears at once)
//   DELETE /api/comments?slug=SLUG&id=ID     -> { ok }   (needs x-admin-key)
import { getStore } from "@netlify/blobs";

export const config = { path: "/api/comments" };

const MAX_NAME = 60;
const MAX_BODY = 4000;
// collapse control chars (keep normal spaces/newlines), then trim
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
const publicOf = ({ hidden, ...c }) => c;

export default async (req) => {
  const store = getStore({ name: "comments", consistency: "strong" });
  const url = new URL(req.url);

  if (req.method === "GET") {
    const slug = clean(url.searchParams.get("slug"));
    if (!slug) return json({ comments: [] });
    const list = (await store.get(key(slug), { type: "json" })) || [];
    const visible = list.filter((c) => !c.hidden).map(publicOf);
    return json({ comments: visible });
  }

  if (req.method === "POST") {
    let b;
    try {
      b = await req.json();
    } catch {
      return json({ error: "Malformed request." }, 400);
    }
    if (clean(b.website)) return json({ ok: true }); // honeypot: silently drop bots
    const slug = clean(b.slug);
    const name = clean(b.name).slice(0, MAX_NAME) || "Anonymous";
    const body = clean(b.body).slice(0, MAX_BODY);
    if (!slug || !body) return json({ error: "A comment is required." }, 400);

    const list = (await store.get(key(slug), { type: "json" })) || [];
    // reject an exact duplicate of the most recent comment (double-submit / flood)
    const last = list[list.length - 1];
    if (last && last.body === body && last.name === name) {
      return json({ comment: publicOf(last) }, 200);
    }
    const c = { id: rid(), name, body, ts: Date.now() };
    list.push(c);
    await store.setJSON(key(slug), list);
    return json({ comment: publicOf(c) }, 201);
  }

  if (req.method === "DELETE") {
    const admin = req.headers.get("x-admin-key");
    if (!admin || admin !== process.env.COMMENTS_ADMIN_KEY) {
      return json({ error: "Unauthorized." }, 401);
    }
    const slug = clean(url.searchParams.get("slug"));
    const id = clean(url.searchParams.get("id"));
    const list = (await store.get(key(slug), { type: "json" })) || [];
    const next = list.filter((c) => c.id !== id);
    await store.setJSON(key(slug), next);
    return json({ ok: true, remaining: next.length });
  }

  return json({ error: "Method not allowed." }, 405);
};
