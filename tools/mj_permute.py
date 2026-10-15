# -*- coding: utf-8 -*-
"""Turn a batch of prompts into one Midjourney permutation prompt.

Midjourney fires one job per option inside {curly braces}, so a whole batch
can be submitted in a single line. The trap is the separator: a comma inside
an option splits it into further options unless it is escaped as \\, — and a
scene description is almost entirely commas. Unescaped, twelve scenes become
a hundred-odd fragments, each its own job, each burning GPU minutes on
nonsense.

So the scenes go inside the braces with every comma escaped, and the shared
house style goes outside, where it is appended to each job and needs no
escaping.

Per-prompt job caps are per plan — Basic 4, Standard 10, Pro 40, Mega 40 at
the time of writing — so the batch is split to a size you name.

    python tools/mj_permute.py tools/mj-prompts-batch-01.md --max 10
"""
import argparse, io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def split_tail(prompt):
    """Separate the scene from the trailing flags (--ar, --style, --v …)."""
    m = re.search(r"\s(--\w[\s\S]*)$", prompt)
    return (prompt[:m.start()].rstrip(), m.group(1).strip()) if m else (prompt.strip(), "")


def common_suffix(scenes):
    """The house-style clause every scene ends with, found rather than typed."""
    parts = [[p.strip() for p in s.split(",")] for s in scenes]
    tail, i = [], 1
    while all(len(p) >= i and p[-i] == parts[0][-i] for p in parts):
        tail.insert(0, parts[0][-i]); i += 1
    return tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--max", type=int, default=6,
                    help="jobs per submission. His account refused 12 with "
                         "\"the limit is 10\" on 2026-10-15, so 10 is the ceiling "
                         "here and 6 is the default that leaves room.")
    a = ap.parse_args()

    text = io.open(a.file, encoding="utf-8").read()
    # the prompts are the fenced blocks that carry Midjourney flags
    blocks = [b.strip() for b in re.findall(r"```([\s\S]*?)```", text)]
    prompts = [b for b in blocks if "--ar" in b]
    if not prompts:
        raise SystemExit("no prompts found in %s" % a.file)

    # the first fenced block in these files is the house-style line itself
    scenes, flags = [], ""
    for p in prompts:
        s, f = split_tail(" ".join(p.split()))
        scenes.append(s); flags = flags or f
    tail = common_suffix(scenes)
    if tail:
        cut = ", ".join(tail)
        scenes = [s[: -len(cut)].rstrip().rstrip(",") if s.endswith(cut) else s
                  for s in scenes]
        # the style line on its own is not a scene
        scenes = [s for s in scenes if s]

    print("%d scenes, %d shared style clauses, flags: %s\n" % (len(scenes), len(tail), flags))

    for i in range(0, len(scenes), a.max):
        chunk = scenes[i:i + a.max]
        opts = " , ".join(s.replace(",", "\\,") for s in chunk)
        line = "{%s}, %s %s" % (opts, ", ".join(tail), flags)
        print("--- submission %d of %d  (%d jobs) ---"
              % (i // a.max + 1, (len(scenes) + a.max - 1) // a.max, len(chunk)))
        print(line)
        print()


if __name__ == "__main__":
    main()
