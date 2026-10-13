"""Screens the event cards in revolutions/*.md for text copied from their likely sources.

The companion of copy_screen.py, whose functions it reuses. Each `## ` card is screened on its own:
every sentence of its body is broken into seven-word shingles and looked up in the corpus texts whose
first author and year match an entry of the card's reference block, and in the Wikipedia article that
best matches the card title. A sentence counts as copied when at least 60 per cent of its shingles
occur in one source. A zero proves nothing about sources outside the corpus, and close paraphrase
passes the screen, so a reviser still opens the cited pages.

Usage: python tools/card_screen.py [revolutions/political.md ...]   (all three files by default)
Results are merged into docs/copy-screen-2026-10-04.json under keys of the form `<file>#<card title>`.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy_screen as cs  # noqa: E402


def cards(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"\A﻿?---\n.*?\n---\n", "", t, flags=re.S)
    for m in re.finditer(r"(?ms)^## (.+?)\n(.*?)(?=^## |\Z)", t):
        yield m.group(1).strip(), m.group(2)


def sentences(body):
    b = re.sub(r"<reference>.*?</reference>", "", body, flags=re.S)
    b = re.sub(r"(?m)^\s*-\s+\w+:\s.*$", "", b)
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(b.split())) if len(s.split()) >= cs.N]


def keys_of(body, corpus_rows):
    m = re.search(r"<reference>(.*?)</reference>", body, re.S)
    return cs.keys_from_block(m.group(1), corpus_rows) if m else set()


def main(paths):
    corpus_rows = cs.load_corpus_rows()
    cache, report = {}, {}
    for path in paths:
        rel = os.path.relpath(path, cs.ROOT).replace("\\", "/")
        for title, body in cards(path):
            srcs = {}
            for k in keys_of(body, corpus_rows):
                if k not in cache:
                    cache[k] = cs.load_corpus_text(k)
                if cache[k]:
                    srcs[k] = cache[k]
            plain = re.sub(r"<br>.*$|\(.*?\)", "", title).strip()
            hit = cs.wiki_search(plain)
            if hit:
                srcs["wikipedia:" + hit] = cs.index_of_text(cs.wiki(hit))
            copied = []
            sents = sentences(body)
            for s in sents:
                sh = cs.shingles(cs.norm(s).split())
                best, best_share, labs = None, 0.0, []
                for name, idx in srcs.items():
                    found = [idx[x] for x in sh if x in idx]
                    share = len(found) / len(sh)
                    if share > best_share:
                        best, best_share, labs = name, share, sorted({lab for lab in found if lab})
                if best_share >= 0.6:
                    copied.append({"sentence": s, "source": best, "share": round(best_share, 2), "pages": labs[:6]})
            report[f"{rel}#{title}"] = {"sentences": len(sents), "copied": copied, "sources_checked": sorted(srcs)}
            print(f"{rel}#{title[:50]:50} {len(copied):3}/{len(sents):3} copied  "
                  f"{', '.join(sorted({c['source'] for c in copied}))[:80]}", flush=True)
    old = json.load(open(cs.OUT, encoding="utf-8")) if os.path.exists(cs.OUT) else {}
    old.update(report)
    json.dump(old, open(cs.OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    args = sys.argv[1:] or [f"{cs.ROOT}/revolutions/{n}.md" for n in ("political", "ideational", "technological")]
    main([a if os.path.isabs(a) else os.path.join(cs.ROOT, a) for a in args])
