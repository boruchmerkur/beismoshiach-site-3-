/* beismoshiach.org — reader comments (no login, appears immediately).
   Talks only to same-origin /api/comments (Netlify Blobs store). No trackers. */
(function () {
  "use strict";
  var mount = document.getElementById("comments");
  if (!mount) return;

  // slug = the article filename without extension (matches the store key)
  var slug = (location.pathname.split("/").pop() || "").replace(/\.html?$/i, "");
  if (!slug) return;

  var API = "/api/comments";
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function when(ts) {
    try {
      return new Date(ts).toLocaleDateString(undefined, {
        year: "numeric", month: "short", day: "numeric",
      });
    } catch (e) { return ""; }
  }
  function para(body) {
    // preserve line breaks, escape everything, no HTML allowed from readers
    return esc(body).replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  }

  mount.innerHTML =
    '<h2 class="cm-h">Comments</h2>' +
    '<div class="cm-list" aria-live="polite"><p class="cm-empty">Loading…</p></div>' +
    '<form class="cm-form" novalidate>' +
    '<p class="cm-lead">Share a thought on this article. Comments are reviewed before they appear.</p>' +
    '<input class="cm-name" name="name" type="text" maxlength="60" placeholder="Your name (optional)" autocomplete="name">' +
    '<textarea class="cm-body" name="body" rows="4" maxlength="4000" placeholder="Your comment…" required></textarea>' +
    '<input class="cm-hp" name="website" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">' +
    '<div class="cm-row"><button class="cm-post" type="submit">Post comment</button>' +
    '<span class="cm-msg" role="status"></span></div>' +
    "</form>";

  var listEl = mount.querySelector(".cm-list");
  var form = mount.querySelector(".cm-form");
  var msg = mount.querySelector(".cm-msg");
  var btn = mount.querySelector(".cm-post");

  function render(list) {
    if (!list || !list.length) {
      listEl.innerHTML = '<p class="cm-empty">No comments yet. Be the first.</p>';
      return;
    }
    listEl.innerHTML = list
      .map(function (c) {
        return (
          '<article class="cm-item"><div class="cm-meta">' +
          '<span class="cm-who">' + esc(c.name || "Anonymous") + "</span>" +
          '<span class="cm-when">' + when(c.ts) + "</span></div>" +
          "<p>" + para(c.body || "") + "</p></article>"
        );
      })
      .join("");
  }

  function load() {
    fetch(API + "?slug=" + encodeURIComponent(slug), { headers: { accept: "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (d) { render(d.comments || []); })
      .catch(function () {
        listEl.innerHTML = '<p class="cm-empty">Comments are unavailable right now.</p>';
      });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var body = form.body.value.trim();
    if (!body) { msg.textContent = "Please write a comment first."; return; }
    btn.disabled = true;
    msg.textContent = "Posting…";
    fetch(API, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        slug: slug,
        name: form.name.value.trim(),
        body: body,
        website: form.website.value,
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.d.pending) throw new Error(res.d.error || "error");
        // comment is held for approval — do NOT show it to the visitor yet
        form.body.value = "";
        msg.textContent = "Thank you — your comment will appear once it’s approved.";
      })
      .catch(function (err) {
        msg.textContent = (err && err.message) || "Could not post. Please try again.";
      })
      .then(function () { btn.disabled = false; });
  });

  load();
})();
