# -*- coding: utf-8 -*-
"""Make a copy page: anything he has to paste somewhere gets buttons.

Markdown files cannot be copied out of comfortably — fenced blocks select
their surrounding chrome, and long single-line prompts wrap into something
that looks like several lines. So whenever the deliverable is text destined
for another box (a Midjourney prompt, a Blogger theme, a post body), it ships
as an HTML page with one textarea per item and Select-all / Copy on each.

    python tools/build_copy_page.py tools/mj-batch-01-permutations.md

Writes "Copy - <title>.html" beside the source. Open it, press Copy, paste.
"""
import argparse, io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHELL = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{--paper:#FFFCF2;--ink:#161A17;--soft:#6b665c;--rule:#e2dccd;--go:#1E5E3A}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);
       font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
  .wrap{max-width:880px;margin:0 auto;padding:2rem 1.2rem 4rem}
  h1{font:600 1.4rem/1.2 Georgia,serif;margin:0 0 .3rem}
  .sub{color:var(--soft);font-size:.9rem;margin:0 0 1.8rem}
  .card{border:1px solid var(--rule);border-radius:4px;background:#fff;
        margin:0 0 1.2rem;overflow:hidden}
  .card-head{display:flex;align-items:center;gap:.6rem;padding:.7rem .9rem;
        border-bottom:1px solid var(--rule);background:#faf7ee}
  .card-head h2{font:600 .95rem/1.3 inherit;margin:0;flex:1}
  .note{color:var(--soft);font-size:.8rem;margin:0}
  button{font:inherit;font-size:.82rem;padding:.4rem .8rem;border-radius:3px;
        border:1px solid var(--rule);background:#fff;cursor:pointer}
  button:hover{border-color:var(--ink)}
  button.primary{background:var(--go);border-color:var(--go);color:#fff}
  .status{color:var(--go);font-size:.8rem;min-width:5.5rem;text-align:right}
  textarea{width:100%;border:0;padding:.9rem;font:13px/1.55 ui-monospace,
        "Cascadia Mono",Consolas,monospace;resize:vertical;background:#fff;
        color:var(--ink);white-space:pre-wrap;word-break:break-word}
  textarea:focus{outline:2px solid var(--go);outline-offset:-2px}
</style></head><body><div class="wrap">
<h1>__TITLE__</h1>
<p class="sub">__SUB__</p>
__CARDS__
</div>
<script>
document.querySelectorAll('.card').forEach(function(card){
  var ta=card.querySelector('textarea'),
      st=card.querySelector('.status'),
      say=function(m){ st.textContent=m; setTimeout(function(){st.textContent='';},2200); };
  card.querySelector('.sel').addEventListener('click',function(){
    ta.focus(); ta.select(); say('selected');
  });
  card.querySelector('.cp').addEventListener('click',function(){
    ta.focus(); ta.select();
    var ok=function(){ say('copied'); };
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(ta.value).then(ok,function(){
        say(document.execCommand('copy')?'copied':'press Ctrl+C');
      });
    } else {
      say(document.execCommand('copy')?'copied':'press Ctrl+C');
    }
  });
});
</script></body></html>
"""

CARD = """<div class="card">
  <div class="card-head"><h2>__H__</h2><p class="note">__N__</p>
    <button class="sel">Select all</button>
    <button class="cp primary">Copy</button>
    <span class="status"></span></div>
  <textarea rows="__R__" spellcheck="false">__BODY__</textarea>
</div>"""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    text = io.open(a.file, encoding="utf-8").read()
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, os.path.basename(a.file)])[1]

    # Every fenced block becomes a card, and the nearest heading above it is
    # its name. Some of these files carry the prompts as bare lines instead —
    # a generated permutation line is one very long line, never fenced — so
    # those are picked up by their Midjourney flags when there is no fence.
    cards, blocks = [], list(re.finditer(r"```[a-z]*\n([\s\S]*?)```", text))
    if not blocks:
        blocks = [m for m in re.finditer(r"^(.*--ar\s.*)$", text, re.M)]
    for m in blocks:
        before = text[:m.start()]
        h = re.findall(r"^#{2,4}\s+(.+)$", before, re.M)
        body = m.group(1).strip()
        rows = min(16, max(4, body.count("\n") + body.count(" ") // 90 + 3))
        cards.append(CARD
                     .replace("__H__", esc(h[-1] if h else "Prompt %d" % (len(cards) + 1)))
                     .replace("__N__", esc("%d characters" % len(body)))
                     .replace("__R__", str(rows))
                     .replace("__BODY__", esc(body)))
    if not cards:
        raise SystemExit("no fenced blocks in %s — nothing to copy" % a.file)

    out = a.out or os.path.join(os.path.dirname(a.file) or ".",
                                "Copy - %s.html" % re.sub(r'[\\/:*?"<>|]', "", title))
    io.open(out, "w", encoding="utf-8", newline="").write(
        SHELL.replace("__TITLE__", esc(title))
             .replace("__SUB__", esc("%d to copy. Click Copy, then paste." % len(cards)))
             .replace("__CARDS__", "\n".join(cards)))
    print("%s  (%d blocks)" % (out, len(cards)))


if __name__ == "__main__":
    main()
