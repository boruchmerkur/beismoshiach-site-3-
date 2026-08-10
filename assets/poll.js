/* beismoshiach.org — the week's question.
   Talks only to same-origin /api/poll (Netlify Blobs). No trackers, no login.

   The mount is EMPTY until the server says there is a question, and it removes
   itself when there isn't. A weekly poll that sits on the landing page saying
   "no poll this week" is worse than no poll at all, and a week will be missed. */
(function () {
  "use strict";
  var mount = document.getElementById("weekpoll");
  if (!mount) return;

  var API = "/api/poll";

  /* Take the kicker with it. A heading left standing over nothing reads as a
     page that failed to load, which is exactly the impression a quiet week
     should not give. */
  function gone() {
    var k = document.getElementById("weekpoll-kick");
    if (k) k.remove();
    mount.remove();
  }

  /* The reader's own token, made in their browser and never sent anywhere else.
     It is what makes one-answer-each work without an account. Clearing site data
     forgets it — which is the honest ceiling for a poll with no login, and the
     same bargain the rest of this site makes. */
  function voter() {
    var k = "bm.voter", v = "";
    try { v = localStorage.getItem(k) || ""; } catch (e) { return ""; }
    if (!/^[a-z0-9]{10,32}$/.test(v)) {
      v = "";
      try {
        var a = new Uint8Array(12);
        crypto.getRandomValues(a);
        for (var i = 0; i < a.length; i++) v += (a[i] % 36).toString(36);
      } catch (e2) {
        v = (Date.now().toString(36) + Math.random().toString(36).slice(2)).slice(0, 20);
      }
      v = v.replace(/[^a-z0-9]/g, "").slice(0, 20);
      try { localStorage.setItem(k, v); } catch (e3) { /* answer still counts once */ }
    }
    return v;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var me = voter();
  var poll = null;

  function tally(p) {
    var c = p.counts || {}, total = 0, i;
    for (i = 0; i < p.options.length; i++) total += c[p.options[i].id] || 0;
    return { c: c, total: total || p.votes || 0 };
  }

  /* Results. The bar is drawn from the share, and the leading answer is marked —
     but the reader's OWN answer is marked differently, because the interesting
     thing about a poll you have just answered is where you stand in it. */
  function results(p, msg) {
    var t = tally(p), rows = "";
    for (var i = 0; i < p.options.length; i++) {
      var o = p.options[i];
      var n = t.c[o.id] || 0;
      var pc = t.total ? Math.round((n / t.total) * 100) : 0;
      rows +=
        '<li class="pl-res' + (p.you === o.id ? " is-you" : "") + '">' +
        '<div class="pl-res-top"><span class="pl-res-lab">' + esc(o.label) +
        (p.you === o.id ? ' <span class="pl-yours">your answer</span>' : "") +
        '</span><span class="pl-res-pc">' + pc + "%</span></div>" +
        '<div class="pl-bar"><i style="width:' + pc + '%"></i></div>' +
        '<div class="pl-res-n">' + n + (n === 1 ? " reader" : " readers") + "</div></li>";
    }
    return (
      '<ol class="pl-results">' + rows + "</ol>" +
      '<p class="pl-foot">' + (msg ? esc(msg) + " · " : "") +
      t.total + (t.total === 1 ? " answer" : " answers") +
      (p.open ? "" : " · this question has closed") + "</p>"
    );
  }

  function ballot(p) {
    var rows = "";
    for (var i = 0; i < p.options.length; i++) {
      var o = p.options[i];
      rows +=
        '<li><label class="pl-opt">' +
        '<input type="radio" name="opt" value="' + esc(o.id) + '">' +
        '<span class="pl-opt-lab">' + esc(o.label) + "</span></label></li>";
    }
    return (
      '<form class="pl-form" novalidate>' +
      '<ul class="pl-opts" role="radiogroup">' + rows + "</ul>" +
      '<div class="pl-extra" hidden>' +
      '<label class="pl-note-lab" for="pl-note">In a few words — for the editor, not published</label>' +
      '<textarea class="pl-note" id="pl-note" name="note" rows="2" maxlength="500" ' +
      'placeholder="Optional."></textarea></div>' +
      '<input class="pl-hp" name="website" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<div class="pl-row"><button class="pl-send" type="submit" disabled>Answer</button>' +
      '<span class="pl-msg" role="status">' +
      (p.votes ? p.votes + (p.votes === 1 ? " reader has answered" : " readers have answered") : "") +
      "</span></div></form>"
    );
  }

  function head(p) {
    return (
      (p.label ? '<p class="pl-eyebrow">' + esc(p.label) + "</p>" : "") +
      '<h2 class="pl-q">' + esc(p.q) + "</h2>" +
      (p.sub ? '<p class="pl-sub">' + esc(p.sub) + "</p>" : "")
    );
  }

  function draw(p, msg) {
    poll = p;
    var body = p.results ? results(p, msg) : ballot(p);
    mount.innerHTML = '<div class="pl-card">' + head(p) + body + "</div>";
    mount.hidden = false;
    if (!p.results) wire();
  }

  function wire() {
    var form = mount.querySelector(".pl-form");
    var btn = mount.querySelector(".pl-send");
    var msg = mount.querySelector(".pl-msg");
    var extra = mount.querySelector(".pl-extra");

    form.addEventListener("change", function () {
      // The note only asks to be written once there is something to say it about.
      if (form.opt && form.opt.value) { btn.disabled = false; extra.hidden = false; }
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var opt = form.opt && form.opt.value;
      if (!opt) { msg.textContent = "Pick one first."; return; }
      btn.disabled = true;
      msg.textContent = "Sending…";
      fetch(API, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          w: poll.w, opt: opt, voter: me,
          note: form.note.value.trim(),
          website: form.website.value,
        }),
      })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!res.ok || !res.d.ok) throw new Error(res.d.error || "Could not send.");
          draw(res.d.poll, res.d.already ? "You had already answered" : "Thank you");
        })
        .catch(function (err) {
          btn.disabled = false;
          msg.textContent = (err && err.message) || "Could not send. Please try again.";
        });
    });
  }

  fetch(API + (me ? "?voter=" + encodeURIComponent(me) : ""), {
    headers: { accept: "application/json" },
  })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d.poll || !d.poll.q) { gone(); return; }   // no question this week
      draw(d.poll, "");
    })
    .catch(gone);
})();
