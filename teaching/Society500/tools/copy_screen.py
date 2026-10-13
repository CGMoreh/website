"""Screens the earlier-layer timeline files for text copied from their likely sources.

For every biography and works file of the people given (or of the earlier layers by default), each
sentence of the body is broken into seven-word shingles and looked up in: the corpus texts that the
cast file lists as the person's sources, corpus texts whose first author and year match an entry
of the file's reference block, and the Wikipedia articles on the person and, for a works file, on
the work. A sentence counts as copied when at least 60 per cent of its shingles occur in one
source. The report gives, per file, the number of copied sentences, the source and the printed page
labels where the corpus text has them, and writes a JSON file that a writer can read.
"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = "D:/GitHub/chrismoreh-source/teaching/Society500"
CORPUS = "D:/ACADEMIC/PUBLICATIONS/BOOKS/2026_Society500/corpus"
CACHE = "D:/AppData/Local/Temp/claude/wiki_cache"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "copy-screen-2026-10-04.json")
os.makedirs(CACHE, exist_ok=True)
N = 7


def norm(s):
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def shingles(words):
    return [" ".join(words[i:i + N]) for i in range(len(words) - N + 1)]


def load_corpus_text(key):
    path = f"{CORPUS}/texts/{key}.txt"
    if not os.path.exists(path):
        return None
    raw = open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r"(=== page \d+ \(label [^)]*\) ===)", raw)
    pages = []
    for i in range(1, len(parts), 2):
        m = re.search(r"page (\d+) \(label ([^)]*)\)", parts[i])
        lab = m.group(2) or f"pdf {m.group(1)}"
        pages.append((lab, norm(parts[i + 1])))
    index = {}
    for lab, txt in pages:
        for sh in shingles(txt.split()):
            index.setdefault(sh, lab)
    return index


def wiki(title):
    safe = re.sub(r"[^\w-]+", "_", title)[:120]
    path = f"{CACHE}/{safe}.txt"
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    q = urllib.parse.quote(title)
    url = (f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&redirects=1"
           f"&format=json&titles={q}")
    try:
        raw = subprocess.run(["curl", "-s", "-m", "40", "-A", "Society500-screen/1.0", url],
                             capture_output=True, text=True, encoding="utf-8").stdout
        pages = json.loads(raw)["query"]["pages"]
        text = "\n".join(p.get("extract", "") for p in pages.values())
    except Exception:
        text = ""
    open(path, "w", encoding="utf-8").write(text)
    return text


def wiki_search(query):
    q = urllib.parse.quote(query)
    url = f"https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&namespace=0&format=json&search={q}"
    try:
        raw = subprocess.run(["curl", "-s", "-m", "40", "-A", "Society500-screen/1.0", url],
                             capture_output=True, text=True, encoding="utf-8").stdout
        res = json.loads(raw)
        return res[1][0] if res[1] else None
    except Exception:
        return None


def index_of_text(text):
    idx = {}
    for sh in shingles(norm(text).split()):
        idx.setdefault(sh, "")
    return idx


def body_sentences(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"\A\ufeff?---\n.*?\n---\n", "", t, flags=re.S)
    t = re.sub(r"<reference>.*?</reference>", "", t, flags=re.S)
    t = re.sub(r"(?m)^#.*$|^\s*-\s+\w+:\s.*$", "", t)
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(t.split())) if len(s.split()) >= N]


def front(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"\A\ufeff?---\n(.*?)\n---", t, re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        mm = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', line)
        if mm:
            out[mm.group(1)] = mm.group(2)
    return out


def load_corpus_rows():
    """(key, authors, year) for every corpus text. Zotero items come from corpus-index.md; the library
    books held outside Zotero (texts/LIB-<Surname>-<title>.txt) are not in the index and carry no
    reliable year, so they are listed with year None and matched on the surname alone."""
    rows = []
    for line in open(f"{CORPUS}/corpus-index.md", encoding="utf-8"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 4 and re.match(r"^[A-Z0-9]{8}$", parts[0]):
            rows.append((parts[0], parts[2], parts[3]))
    for path in glob.glob(f"{CORPUS}/texts/LIB-*.txt"):
        key = os.path.basename(path)[:-4]
        rows.append((key, key[4:].replace("-", " "), None))
    return rows


def keys_from_block(block, corpus_rows):
    """Corpus keys for the entries of a reference block: same year and the surname as a whole word
    among the authors, or, for a library book, the surname at the head of its file name."""
    keys = set()
    for entry in re.findall(r"^([A-Z][\w'’\- ]+?),.*?\b(1[5-9]\d\d|20\d\d)\b", block, re.M):
        sur, yr = entry[0].split()[-1].lower(), entry[1]
        for key, authors, year in corpus_rows:
            if year is None:
                if re.match(rf"lib-(?:[a-z]+-)?{re.escape(sur)}-", key.lower()):
                    keys.add(key)
            elif year == yr and re.search(rf"(?<![\w-]){re.escape(sur)}(?![\w-])", authors.lower()):
                keys.add(key)
    return keys


def ref_keys(path, corpus_rows):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"<reference>(.*?)</reference>", t, re.S)
    return keys_from_block(m.group(1), corpus_rows) if m else set()


def main(ids):
    cast = {r["id"]: r for r in csv.DictReader(open(f"{ROOT}/docs/cast-2026-09.csv", encoding="utf-8-sig"))}
    corpus_rows = load_corpus_rows()
    cache = {}
    report = {}
    for pid in ids:
        row = cast.get(pid, {})
        files = [f"{ROOT}/author_bios/{pid}.md"] + sorted(glob.glob(f"{ROOT}/author_works/{pid}_*.md"))
        person_keys = set(k for k in re.split(r"[;,\s]+", row.get("sources", "")) if k)
        person_wiki = wiki(row.get("author", pid)) if row else ""
        for path in files:
            if not os.path.exists(path):
                continue
            keys = set(person_keys) | ref_keys(path, corpus_rows)
            srcs = {}
            for k in keys:
                if k not in cache:
                    cache[k] = load_corpus_text(k)
                if cache[k]:
                    srcs[k] = cache[k]
            srcs["wikipedia:" + row.get("author", pid)] = index_of_text(person_wiki)
            if "/author_works/" in path:
                fm = front(path)
                title = fm.get("eng_title") or fm.get("orig_title") or ""
                if title:
                    hit = wiki_search(f"{title} {row.get('author', '')}") or wiki_search(title)
                    if hit:
                        srcs["wikipedia:" + hit] = index_of_text(wiki(hit))
            copied = []
            sents = body_sentences(path)
            for s in sents:
                sh = shingles(norm(s).split())
                best, best_share, labs = None, 0.0, []
                for name, idx in srcs.items():
                    found = [idx[x] for x in sh if x in idx]
                    share = len(found) / len(sh)
                    if share > best_share:
                        best, best_share, labs = name, share, sorted({l for l in found if l})
                if best_share >= 0.6:
                    copied.append({"sentence": s, "source": best, "share": round(best_share, 2), "pages": labs[:6]})
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            report[rel] = {"sentences": len(sents), "copied": copied, "sources_checked": sorted(srcs)}
            print(f"{rel:60} {len(copied):3}/{len(sents):3} copied  "
                  f"{', '.join(sorted({c['source'] for c in copied}))[:90]}", flush=True)
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    old.update(report)
    json.dump(old, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
