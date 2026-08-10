// The week's question for beismoshiach.org — v2 Netlify Function.
//
// A weekly is the one publication where a weekly poll is not a gimmick: the
// magazine already asks the readership something every seven days, it just does
// it in print and never hears back. This is the hearing-back.
//
// Storage is Netlify Blobs, in this site's own account. Same posture as
// /api/comments: no third party, no tracker, no login, nothing about a reader
// stored except an opaque token their own browser made up.
//
// THREE THINGS SHAPE THIS
//
//   THE EDITOR OWNS THE CLOCK. There is no cron and no date arithmetic in here.
//   A poll is "this week's" because the editor pointed `current` at it. The
//   landing page already computes the week from assets/weekly.json; duplicating
//   that rule in a second place is how the two silently disagree. So the widget
//   asks "what is current" and is told, and the week label is only ever a label.
//
//   THE COUNT MUST BE AUDITABLE. Each vote is its own blob (`v/<week>/<voter>`),
//   which is what makes one-vote-per-reader work at all: the key IS the identity,
//   so a second vote collides with itself instead of racing. The tallies on the
//   poll record are a running aggregate on top of that — fast to read, and able
//   to drift, exactly like the totals on torah.today's /api/build. `recount`
//   rebuilds them from the individual votes, which are the record of truth.
//
//   THE NOTE IS NEVER PUBLISHED. A voter may add a few words. They are shown to
//   nobody — not on the page, not in the public JSON — and exist so the editor
//   reads what the readership actually meant before writing next week's issue.
//   Nothing a reader writes here appears under the magazine's name by accident.
//
//   GET    /api/poll                      -> the current poll, public view
//   GET    /api/poll?w=WEEK               -> that week's poll, public view
//   GET    /api/poll?voter=ID             -> ...plus `you`, the option you chose
//   GET    /api/poll?all=1                -> every poll incl. notes  (admin)
//   POST   /api/poll {w,opt,voter,note}   -> cast a vote
//   PUT    /api/poll                      -> write/replace a week's poll (admin)
//   PATCH  /api/poll?w=WEEK&act=...       -> current|close|open|recount  (admin)
//   DELETE /api/poll?w=WEEK               -> drop a poll and its votes  (admin)
import { getStore } from "@netlify/blobs";

export const config = { path: "/api/poll" };

const MAX_Q = 240;
const MAX_LABEL = 120;
const MAX_NOTE = 500; // a few words for the editor, not an essay
const MAX_OPTIONS = 8;
const MIN_OPTIONS = 2;
const MAX_SUB = 60; // a line under the question, if the question needs one

// A week key is the Shabbos date the landing page's schedule already uses.
const WEEK_RE = /^\d{4}-\d{2}-\d{2}$/;
// The voter token is made by the reader's own browser. Nothing is derived from
// it and it is never shown; it exists only so a second vote lands on the same key.
const VOTER_RE = /^[a-z0-9]{10,32}$/;
const OPT_RE = /^o[1-8]$/;

const clean = (s) =>
  Array.from(String(s ?? ""))
    .filter((c) => { const n = c.charCodeAt(0); return n >= 32 || n === 9 || n === 10 || n === 13; })
    .join("")
    .trim();

const pkey = (w) => "w/" + w;
const vkey = (w, voter) => "v/" + w + "/" + voter;

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });

// The admin key is the one this site already has. A second secret to lose is not
// better security, it is one more thing that quietly stops matching.
const isAdmin = (req) =>
  !!process.env.COMMENTS_ADMIN_KEY && req.headers.get("x-admin-key") === process.env.COMMENTS_ADMIN_KEY;

/* What a visitor is allowed to see.
   `reveal` decides whether the tallies travel at all: on "after" (the default)
   a reader who has not voted is not told the standings, because being shown
   which way the room is leaning before you answer is how a poll stops measuring
   anything. Withholding it on the CLIENT would be theatre — the numbers would
   still be sitting in the response — so they are withheld here. */
function publicView(p, you) {
  const shown = !!(you || !p.open || p.reveal === "always");
  const out = {
    w: p.w,
    q: p.q,
    sub: p.sub || "",
    label: p.label || "",
    options: (p.options || []).map((o) => ({ id: o.id, label: o.label })),
    votes: p.votes || 0,
    open: !!p.open,
    reveal: p.reveal || "after",
    results: shown,
    you: you || null,
  };
  if (shown) out.counts = p.counts || {};
  return out;
}

const blankCounts = (options) => {
  const c = {};
  for (const o of options) c[o.id] = 0;
  return c;
};

export default async (req) => {
  const store = getStore({ name: "poll", consistency: "strong" });
  const url = new URL(req.url);

  const readPoll = async (w) => {
    if (!WEEK_RE.test(w)) return null;
    try { return await store.get(pkey(w), { type: "json" }); } catch { return null; }
  };
  const currentWeek = async () => {
    try {
      const c = await store.get("current", { type: "json" });
      return c && WEEK_RE.test(c.w || "") ? c.w : "";
    } catch { return ""; }
  };

  // ---- read ---------------------------------------------------------------
  if (req.method === "GET") {
    // admin: every poll, with the notes readers left and the raw votes behind
    // each tally. This is the view the next issue gets written from.
    if (url.searchParams.get("all") === "1") {
      if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
      const cur = await currentWeek();
      const { blobs } = await store.list({ prefix: "w/" });
      const polls = [];
      for (const b of blobs) {
        const p = await store.get(b.key, { type: "json" });
        if (!p) continue;
        const notes = [];
        const { blobs: vb } = await store.list({ prefix: "v/" + p.w + "/" });
        for (const v of vb) {
          const rec = await store.get(v.key, { type: "json" });
          if (rec && rec.note) notes.push({ opt: rec.opt, note: rec.note, ts: rec.ts });
        }
        notes.sort((a, z) => z.ts - a.ts);
        polls.push({ ...p, cast: vb.length, notes, current: p.w === cur });
      }
      polls.sort((a, z) => String(z.w).localeCompare(String(a.w)));
      return json({ polls, current: cur });
    }

    let w = clean(url.searchParams.get("w"));
    if (!w) w = await currentWeek();
    if (!WEEK_RE.test(w)) return json({ poll: null });

    const p = await readPoll(w);
    if (!p) return json({ poll: null });

    // Has this reader already answered? The vote's key IS the question.
    let you = null;
    const voter = clean(url.searchParams.get("voter"));
    if (VOTER_RE.test(voter)) {
      try {
        const v = await store.get(vkey(w, voter), { type: "json" });
        if (v && v.opt) you = v.opt;
      } catch { /* not voted */ }
    }
    return json({ poll: publicView(p, you) });
  }

  // ---- a reader answers ---------------------------------------------------
  if (req.method === "POST") {
    let b;
    try { b = await req.json(); } catch { return json({ error: "Malformed request." }, 400); }
    if (clean(b.website)) return json({ ok: true }); // honeypot, same as comments

    const w = clean(b.w);
    const voter = clean(b.voter).toLowerCase();
    const opt = clean(b.opt);
    if (!WEEK_RE.test(w)) return json({ error: "No such week." }, 400);
    if (!VOTER_RE.test(voter)) return json({ error: "Missing voter token." }, 400);
    if (!OPT_RE.test(opt)) return json({ error: "Pick one of the answers." }, 400);

    const p = await readPoll(w);
    if (!p) return json({ error: "No such poll." }, 404);
    if (!p.open) return json({ error: "This week's question has closed." }, 409);
    if (!(p.options || []).some((o) => o.id === opt))
      return json({ error: "That answer is not on this question." }, 400);

    const note = clean(b.note).slice(0, MAX_NOTE);

    /* One vote each, and no take-backs once counted. The key is derived from the
       voter, so a resubmit — a double tap, a retry, a second tab — writes to the
       same place instead of adding a second ballot. A reader who HAS voted may
       still add or change their note, since nothing public turns on it. */
    let prior = null;
    try { prior = await store.get(vkey(w, voter), { type: "json" }); } catch { /* new */ }
    if (prior && prior.opt) {
      if (note && note !== prior.note) {
        await store.setJSON(vkey(w, voter), { ...prior, note });
      }
      return json({ ok: true, already: true, poll: publicView(p, prior.opt) });
    }

    await store.setJSON(vkey(w, voter), { opt, note, ts: Date.now() });

    // Fold this one into the running tallies. `recount` is what puts them right
    // if a write ever races; the individual votes above are the record.
    const counts = { ...blankCounts(p.options || []), ...(p.counts || {}) };
    counts[opt] = (counts[opt] || 0) + 1;
    const next = { ...p, counts, votes: (p.votes || 0) + 1 };
    await store.setJSON(pkey(w), next);

    return json({ ok: true, poll: publicView(next, opt) }, 201);
  }

  // ---- the editor writes the question -------------------------------------
  if (req.method === "PUT") {
    if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
    let b;
    try { b = await req.json(); } catch { return json({ error: "Malformed request." }, 400); }

    const w = clean(b.w);
    if (!WEEK_RE.test(w)) return json({ error: "A week is YYYY-MM-DD." }, 400);
    const q = clean(b.q).slice(0, MAX_Q);
    if (!q) return json({ error: "The question is required." }, 400);

    const labels = (Array.isArray(b.options) ? b.options : [])
      .map((s) => clean(s).slice(0, MAX_LABEL))
      .filter(Boolean)
      .slice(0, MAX_OPTIONS);
    if (labels.length < MIN_OPTIONS)
      return json({ error: "Give at least two answers." }, 400);

    const prev = await readPoll(w);

    /* Once anyone has answered, the answers are frozen. The tallies are keyed by
       option id, so editing the list would re-point counts that were cast against
       different words — the numbers would survive and stop meaning anything.
       Wording of the question can still be fixed; the choices cannot. */
    if (prev && (prev.votes || 0) > 0) {
      const same =
        (prev.options || []).length === labels.length &&
        (prev.options || []).every((o, i) => o.label === labels[i]);
      if (!same)
        return json({
          error: "This question already has " + prev.votes +
            " answers, so its choices are fixed. Delete it, or open a new week.",
        }, 409);
    }

    const options = labels.map((label, i) => ({ id: "o" + (i + 1), label }));
    const rec = {
      w,
      q,
      sub: clean(b.sub).slice(0, MAX_SUB),
      label: clean(b.label).slice(0, 80),  // "Parshas Shoftim · 2 Elul", for the eyebrow
      options,
      counts: prev ? { ...blankCounts(options), ...(prev.counts || {}) } : blankCounts(options),
      votes: prev ? prev.votes || 0 : 0,
      open: b.open === false ? false : true,
      reveal: b.reveal === "always" ? "always" : "after",
      made: prev ? prev.made : Date.now(),
      edited: Date.now(),
    };
    await store.setJSON(pkey(w), rec);
    if (b.current) await store.setJSON("current", { w });
    return json({ ok: true, poll: rec, current: !!b.current });
  }

  if (req.method === "PATCH") {
    if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
    const w = clean(url.searchParams.get("w"));
    const act = clean(url.searchParams.get("act"));
    const p = await readPoll(w);
    if (!p) return json({ error: "No such poll." }, 404);

    if (act === "current") {
      await store.setJSON("current", { w });
      return json({ ok: true, current: w });
    }
    if (act === "open" || act === "close") {
      await store.setJSON(pkey(w), { ...p, open: act === "open", edited: Date.now() });
      return json({ ok: true, open: act === "open" });
    }
    if (act === "recount") {
      // Rebuild the tallies from the votes themselves. A running aggregate can
      // only ever be as good as the deltas folded into it; this is the number
      // worth publishing.
      const counts = blankCounts(p.options || []);
      let votes = 0;
      const { blobs } = await store.list({ prefix: "v/" + w + "/" });
      for (const v of blobs) {
        const rec = await store.get(v.key, { type: "json" });
        if (!rec || !rec.opt || !(p.options || []).some((o) => o.id === rec.opt)) continue;
        counts[rec.opt] = (counts[rec.opt] || 0) + 1;
        votes += 1;
      }
      const next = { ...p, counts, votes, recounted: Date.now() };
      await store.setJSON(pkey(w), next);
      return json({ ok: true, poll: next });
    }
    return json({ error: "Unknown action." }, 400);
  }

  if (req.method === "DELETE") {
    if (!isAdmin(req)) return json({ error: "Unauthorized." }, 401);
    const w = clean(url.searchParams.get("w"));
    if (!WEEK_RE.test(w)) return json({ error: "A week is YYYY-MM-DD." }, 400);
    const { blobs } = await store.list({ prefix: "v/" + w + "/" });
    for (const v of blobs) await store.delete(v.key);
    await store.delete(pkey(w));
    const cur = await currentWeek();
    if (cur === w) await store.delete("current");
    return json({ ok: true, votesDropped: blobs.length });
  }

  return json({ error: "Method not allowed." }, 405);
};
