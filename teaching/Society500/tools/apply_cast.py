"""Writes the curated `period` and `tags` of the cast file into the front matter of the biographies.

Usage: python tools/apply_cast.py [--dry-run] [id ...]
Reads docs/cast-2026-09.csv (columns id, periods, tags among others; semicolon-separated lists) and, for
every biography file author_bios/<id>.md that exists, replaces or inserts the `period:` and `tags:` lines
of its YAML front matter with the cast file's values as flow lists (`period: [origins, consolidation]`).
Other front-matter lines and the body are left byte for byte as they are. Ids given on the command line
restrict the run; --dry-run prints what would change. Rows whose biography file does not exist are listed
at the end, since those are the people still to be written.
"""
import csv, io, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAST = os.path.join(HERE, "docs", "cast-2026-09.csv")
BIOS = os.path.join(HERE, "author_bios")
PERIODS = {"sources", "origins", "consolidation", "crisis", "reconstruction", "decentring"}
TAGS = {"critical", "utopian", "revolutionary", "historical", "statistical", "civic", "biological",
        "cultural", "relational"}

args = [a for a in sys.argv[1:] if not a.startswith("--")]
dry = "--dry-run" in sys.argv


def flow(values):
    return "[" + ", ".join(values) + "]"


def split(cell):
    return [v.strip().lower() for v in re.split(r"[;,]", cell or "") if v.strip()]


rows = list(csv.DictReader(io.open(CAST, encoding="utf-8-sig")))
missing, changed, unchanged, bad = [], [], [], []
for row in rows:
    pid = row["id"].strip()
    if args and pid not in args:
        continue
    periods, tags = split(row.get("periods")), split(row.get("tags"))
    if not periods or not set(periods) <= PERIODS or not set(tags) <= TAGS:
        bad.append((pid, periods, tags)); continue
    path = os.path.join(BIOS, pid + ".md")
    if not os.path.exists(path):
        missing.append(pid); continue
    text = io.open(path, encoding="utf-8").read()
    bom = text.startswith("\ufeff")          # some files open with a byte-order mark, kept as found
    if bom:
        text = text[1:]
    # The opening delimiter is the first line and the closing one is the first later line of dashes
    parts = text[4:].split("\n---", 1) if text.startswith("---\n") else None
    if not parts or len(parts) < 2:
        bad.append((pid, "no front matter", "")); continue
    head, fm, rest = "---", parts[0], parts[1]
    lines = fm.split("\n")
    new_period, new_tags = "period: " + flow(periods), "tags: " + flow(tags)
    out, seen_p, seen_t = [], False, False
    for line in lines:
        if re.match(r"^period\s*:", line):
            out.append(new_period); seen_p = True
        elif re.match(r"^tags\s*:", line):
            out.append(new_tags); seen_t = True
        else:
            out.append(line)
    # A file without the fields gets them before `status`, or at the end of the block
    for field, seen in ((new_period, seen_p), (new_tags, seen_t)):
        if not seen:
            idx = next((i for i, l in enumerate(out) if re.match(r"^status\s*:", l)), None)
            out.insert(idx if idx is not None else len(out), field)
    new_fm = "\n".join(out)
    if new_fm == fm:
        unchanged.append(pid); continue
    changed.append(pid)
    if not dry:
        io.open(path, "w", encoding="utf-8", newline="\n").write(("\ufeff" if bom else "") + head + "\n" + new_fm + "\n---" + rest)

print(f"changed {len(changed)}: {' '.join(changed)}")
print(f"unchanged {len(unchanged)}")
if bad:
    print("rows with values outside the vocabularies or files without front matter:")
    for b in bad:
        print("  ", b)
print(f"biographies still to write ({len(missing)}): {' '.join(missing)}")
