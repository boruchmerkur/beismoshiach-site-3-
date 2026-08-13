/* bilingual.js — set the translated sichos as parallel text.

   The sicha translations were exported as one long stack: an English
   paragraph, then the Hebrew it renders, then the next English paragraph, and
   so on down the page. Read that way you lose the pairing — by the time you
   reach the Hebrew you have left the English behind.

   This pairs them back up: Hebrew on the left, its English on the right, one
   row per verse.

   It rearranges nothing textual. The original <p> elements are MOVED, never
   rewritten, re-encoded or regenerated — the same nodes, with their footnote
   links and emphasis intact, placed into a two-column row. Nothing is dropped:
   a paragraph that is not half of a pair is left exactly where it sits. */
(function () {
  'use strict';

  var HEB = /[֐-׿]/g;              // the Hebrew block
  var LAT = /[A-Za-z]/g;

  function count(s, re) { var m = s.match(re); return m ? m.length : 0; }

  /* 'H', 'E', or '' for anything that is neither — a caption, a rule, a
     paragraph holding only an image. Short strings are left alone: a stray
     "5752" or a lone quotation mark should not decide a column. */
  function side(el) {
    if (el.tagName !== 'P') return '';
    if (el.querySelector('img,iframe,figure')) return '';
    var s = el.textContent || '';
    var h = count(s, HEB), l = count(s, LAT);
    if (h >= 8 && h > l) return 'H';
    if (l >= 8 && l > h) return 'E';
    return '';
  }

  function pair(body) {
    var kids = [].slice.call(body.children);
    var made = 0;
    for (var i = 0; i < kids.length - 1; i++) {
      if (side(kids[i]) !== 'E' || side(kids[i + 1]) !== 'H') continue;
      var en = kids[i], he = kids[i + 1];

      var row = document.createElement('div');
      row.className = 'bi';
      var hc = document.createElement('div');
      hc.className = 'bi-he';
      hc.setAttribute('dir', 'rtl');
      hc.setAttribute('lang', 'he');
      var ec = document.createElement('div');
      ec.className = 'bi-en';

      body.insertBefore(row, en);
      hc.appendChild(he);                    // Hebrew first, so it lands left
      ec.appendChild(en);
      row.appendChild(hc);
      row.appendChild(ec);

      made++;
      i++;                                   // the Hebrew is spoken for
    }
    return made;
  }

  function go() {
    var body = document.querySelector('.entry-body');
    if (!body || body.classList.contains('paired')) return;
    /* The Hebrew side of these pages is already right-to-left throughout;
       pairing it against itself would mean nothing. */
    if (document.querySelector('.entry.rtl') || document.body.classList.contains('he-body')) return;
    if (pair(body) >= 3) body.classList.add('paired');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', go);
  } else {
    go();
  }
})();
