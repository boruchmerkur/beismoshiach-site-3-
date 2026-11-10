/* The side column on article pages: the author, his other pieces, this week's parsha.
   Data from tools/build_side.py (assets/side/). Loaded by comments.js, which every
   article already loads, so no article file had to change. His ruling 2026-11-10. */
(function () {
  var entry = document.querySelector('main.wrap > article.entry');
  if (!entry || !/\/articles\//.test(location.pathname)) return;
  var au = entry.querySelector('.entry-eyebrow .au');
  var name = au ? au.textContent.trim() : '';
  var here = location.pathname.split('/').pop().replace(/\.html$/, '');
  function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'unknown'; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function get(u) { return fetch(u).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }

  Promise.all([name ? get('/assets/side/a/' + slug(name) + '.json') : null, get('/assets/side/week.json')]).then(function (res) {
    var a = res[0], wk = res[1], parts = [];
    if (a && a.items) {
      var more = a.items.filter(function (i) { return i.s !== here; }).slice(0, 5);
      if (more.length) {
        parts.push('<div class="bm-side-au">' + (a.img ? '<img src="' + esc(a.img) + '" alt="' + esc(a.name) + '" width="56" height="56">' : '') +
          '<div><b>' + esc(a.name) + '</b></div></div>' +
          '<p class="bm-side-k">More by ' + esc(a.name) + '</p><ul class="bm-side-list">' +
          more.map(function (i) { return '<li><a href="' + esc(i.s) + '.html">' + esc(i.t) + '</a></li>'; }).join('') + '</ul>');
      }
    }
    if (wk && wk.weeks) {
      var today = new Date().toISOString().slice(0, 10);
      var w = wk.weeks.filter(function (x) { return x.w >= today; })[0];
      if (w && w.items && w.items.length) {
        parts.push('<p class="bm-side-k">This week: ' + esc(w.label) + '</p><ul class="bm-side-list">' +
          w.items.filter(function (i) { return i.s !== here; }).slice(0, 4).map(function (i) { return '<li><a href="' + esc(i.s) + '.html">' + esc(i.t) + '</a></li>'; }).join('') +
          '</ul><p class="bm-side-all"><a href="tag/' + esc(w.tag) + '.html">Every article on ' + esc(w.label.replace(/^Parshas /, '')) + ' →</a></p>');
      }
    }
    if (!parts.length) return;
    var aside = document.createElement('aside');
    aside.className = 'bm-side';
    aside.setAttribute('aria-label', 'More to read');
    aside.innerHTML = parts.join('');
    entry.parentNode.classList.add('has-side');
    entry.parentNode.insertBefore(aside, entry.nextSibling);
  });
})();
