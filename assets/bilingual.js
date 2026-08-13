/* bilingual.js — make the parallel sicha tables fit the page.

   The translated sichos are already laid out as two-column tables, Hebrew
   beside its English, and because the export left direction:rtl on them the
   Hebrew already falls on the left. What it also left is Word's fixed pixel
   widths — width="281" and width="256" on every cell — frozen to the column
   width of a document written years ago on someone else's screen.

   So the table sits 538px wide inside a 720px column, wasting 182px of the
   measure it was given, and on a phone it does not stack: it squeezes to two
   columns of about 178px and 149px, which is no width at all for pointed
   Hebrew.

   This drops those width attributes and lets the table use the column it is
   in — half each, side by side — then stacks the two languages on narrow
   screens with the Hebrew still first.

   It touches attributes and classes only. No text is read, rewritten,
   re-encoded or moved; the cells and everything in them are left exactly as
   they are stored. */
(function () {
  'use strict';

  var HEB = /[֐-׿]/g;
  var LAT = /[A-Za-z]/g;
  function n(s, re) { var m = (s || '').match(re); return m ? m.length : 0; }

  function unfreeze(el) {
    el.removeAttribute('width');
    if (el.style) {
      el.style.width = '';
      el.style.minWidth = '';
      el.style.maxWidth = '';
    }
  }

  /* Which column is which, decided over the whole table rather than one row:
     a single row can be a heading, a citation, or empty. */
  function columns(rows) {
    var h = [0, 0], l = [0, 0];
    for (var i = 0; i < rows.length; i++) {
      var c = rows[i].cells;
      if (c.length !== 2) continue;
      for (var j = 0; j < 2; j++) {
        h[j] += n(c[j].textContent, HEB);
        l[j] += n(c[j].textContent, LAT);
      }
    }
    if (h[1] > l[1] && l[0] > h[0]) return { he: 1, en: 0 };
    if (h[0] > l[0] && l[1] > h[1]) return { he: 0, en: 1 };
    return null;                       // not a bilingual pair of columns
  }

  function fix(table) {
    var rows = [].slice.call(table.rows);
    var paired = rows.filter(function (r) { return r.cells.length === 2; });
    if (paired.length < 3) return false;
    var col = columns(paired);
    if (!col) return false;

    unfreeze(table);
    table.classList.add('bi-table');
    rows.forEach(function (r) {
      var c = r.cells;
      for (var i = 0; i < c.length; i++) unfreeze(c[i]);
      if (c.length === 2) {
        c[col.he].classList.add('bi-he');
        c[col.en].classList.add('bi-en');
      } else if (c.length === 1 && !c[0].hasAttribute('colspan')) {
        /* A lone cell in a two-column table is a heading or a note. Without
           this it is trapped in one column while the other sits empty. */
        c[0].setAttribute('colspan', '2');
        c[0].classList.add('bi-full');
      }
    });
    return true;
  }

  function go() {
    var body = document.querySelector('.entry-body');
    if (!body) return;
    /* Pages that are Hebrew throughout are already right-to-left end to end;
       there is no second language here to set beside anything. */
    if (document.querySelector('.entry.rtl') || document.body.classList.contains('he-body')) return;
    var tables = body.querySelectorAll('table');
    var done = 0;
    for (var i = 0; i < tables.length; i++) if (fix(tables[i])) done++;
    if (done) body.classList.add('has-parallel');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', go);
  } else {
    go();
  }
})();
