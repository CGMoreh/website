"""Sweeps timeline content files for the prose rules of the writers' brief and section 9 of the voice guide.

Usage: python tools/sweep_prose.py [--quiet] FILE ...
       python tools/sweep_prose.py [--quiet] --new     every untracked or modified file under author_bios,
                                                       author_works and revolutions, as git reports them

A file is classified by its folder: author_bios (a biography), author_works (a works summary),
revolutions (event cards); anything else is swept as plain prose. Body words exclude the front matter,
the parenthetical citations and the reference block.

ERROR lines are breaches of a stated rule: an em-dash or a double hyphen in the body, a section sign, a
banned word outside a quotation, a question mark in running prose, front matter with a missing field or
a value outside the vocabularies or unequal to the cast file (docs/cast-2026-09.csv), an in-text
citation with no entry in the reference block, a missing reference block, more than one parenthetical
dash, semicolon or colon in a paragraph, a sentence-initial connective of the banned kind, a superlative
of the banned kind, an announcement opener, revision residue, assessment language addressed to a reader
("a first-year should carry away", "the lesson is"), a Zotero key or a note about the file that was read or the checking that was done (these
belong in docs/editorial-notes/), a reference to the timeline, a module, a course or
a book project, and a closing paragraph of a biography that does not name the person's traditions.
REVIEW lines are heuristics that need a reader: a word that is banned only in one sense (account,
signal, vital, rich), a perception verb, the word student, a possessive on a lowercase noun, a head
noun followed by a name and a verb with no relativiser, a not-but inversion, a payoff colon, a
sentence-length quotation without a page locator, curly quotation marks, a short paragraph-final
sentence, and a body outside the usual range (a biography under 150 or over 650 words, a works summary
under 50 or over 260, an event card under 100 or over 300), since length follows the complexity of the
person or the work and is judged, never capped. Quotations in double marks are excluded from the word
checks, as the rules require. The exit code is 1 when any file has an ERROR, so a writer runs the sweep
until it exits 0 and then explains every REVIEW left standing.
"""
import csv, io, os, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAST = os.path.join(HERE, "docs", "cast-2026-09.csv")
PERIODS = {"sources", "origins", "consolidation", "crisis", "reconstruction", "decentring"}
TAGS = {"critical", "utopian", "revolutionary", "historical", "statistical", "civic", "biological",
        "cultural", "relational"}
SIZES = {"bio": (150, 650), "works": (50, 260), "card": (100, 300)}    # the usual range, for a reader's judgement

# A match outside a quotation is an ERROR
HARD = [
    (r"(?i)crystalli[sz]\w*", "crystallise"),
    (r"(?i)\b(first-years?|first year students?|carry away|carried away|take away|takeaways?|take-aways?|should remember|"
     r"worth remembering|the lesson|for our purposes)\b", "assessment language: no sentence grades what a reader is to remember"),
    (r"(?i)\b(the timeline|this timeline|SOC1030|this module|the module|this course|the course|this book|our book|"
     r"Part 1|Week \d|the lecture notes|this lecture)\b", "attached to the timeline, a course or a book project: descriptions stand on their own"),
    (r"\bheadlines?\b", "headline as a metaphor"),
    (r"\bhonest(ly)?\b", "honest as an evaluation"),
    (r"\bturn(s|ed|ing)? (mainly |largely |entirely |partly )?on\b", "turn on in the sense of depend on"),
    (r"\b(delv\w*|crucial\w*|foster\w*|leverag\w*|intricate\w*|underscor\w*|seamless\w*|pivotal|testament|"
     r"tapestr\w*|elevat\w*|showcas\w*|unpack\w*)\b", "surge vocabulary"),
    (r"\b(journey\w*|navigat\w*)\b", "journey or navigate as a metaphor"),
    (r"\b(clearest|sharpest|starkest|most striking|most telling|fingerprint)\b", "superlative of the banned kind"),
    (r"(^|[.!?]\s+)(Notably|Crucially|Strikingly|Importantly|Moreover|Furthermore|Additionally),",
     "sentence-initial connective"),
    (r"\b(fares no better|finds (even )?less support|even less|no better)\b", "revision residue"),
    (r"\bWhat .* (was|is) .*, not\b", "standalone inversion aphorism"),
]
# Anything addressed to an editor is an ERROR wherever it stands, the reference block included: the
# published texts carry references only, and the notes live in docs/editorial-notes/
EDITORIAL = re.compile(
    r"BS[[A-Z0-9]{8}BS]|BSbLIB-[BSw-]+|BSbPDFBSb|(?i:BSbepub p|page labels?|running (heads?|feet)|text layer|BSbOCRBSb|BSbEPUBBSb|"
    r"BSbZoteroBSb|corpus (index|text)|held (text|copy|texts|copies)|BSbnot heldBSb|the library (holds|copy)|"
    r"library copy|copy on disk|cast (file|record)|front matter|checked against|was not consulted|consulted for this|FOR-IMPORT|"
    r"BSbthe extractionBSb(?! of)|BSbsheet numbers?BSb)|BSbthe corpusBSb".replace("BS", chr(92)))

# A match needs a reader: REVIEW
SOFT = [
    (r"\baccounts?\b", "account: banned when it means a view or a theory"),
    (r"\bsignals?\b", "signal: banned outside its technical sense"),
    (r"\b(vital|robust|rich|dynamic|comprehensive|landscape)\b", "praise adjective or metaphor: check the sense"),
    (r"\b(see|saw|seen|witness\w*)\b", "perception verb: only for someone who looked"),
    (r"\bstudents?\b", "student: a historical student is fine, a reader addressed as one is not"),
    (r"\b[a-z]+'s\b", "possessive on a lowercase noun: expand it unless the noun is a person"),
    (r"\bnot\b[^.;:]{2,60}\bbut\b", "not-but inversion: allowed only where the contrast is the argument"),
    (r", not [a-z]+\.$", "inversion kicker at the end of a sentence"),
]
# A lowercase head noun, a capitalised name and a verb with no relativiser between: "the law Quetelet proposed"
CONTACT = re.compile(r"\b([a-z]+) ([A-Z][\w-]+(?: (?:and|&) [A-Z][\w-]+)?) "
                     r"(defines|defined|classifies|treats|treated|records|recorded|labels|describes|described|calls|"
                     r"called|uses|used|proposed|made|wrote|gave|drew|took|held|set|read|reads)\b")
FUNCTION_WORDS = {"and", "but", "or", "that", "which", "as", "when", "where", "while", "than", "if", "because",
                  "so", "then", "since", "whom", "what", "how", "although", "though", "whereas", "until", "before",
                  "after", "for", "with", "by", "to", "in", "on", "of", "from", "at", "into", "under", "over", "whose"}
CURLY = re.compile(r"[‘’“”]")

CITE = re.compile(r"\(([^()]*?\b1\d{3}[a-z]?\b[^()]*|[^()]*?\b20\d{2}[a-z]?\b[^()]*)\)")   # (Author year: page)
CITE_YEAR = re.compile(r"\b(1\d{3}|20\d{2})[a-z]?\b")
NAMED_CITE = re.compile(r"\b([A-Z][\w'-]+)(?: (?:and|&) [A-Z][\w'-]+)? \((1\d{3}|20\d{2})[a-z]?(?::[^)]*)?\)")  # Skinner (1978a: 52)
PAGE_MARK = re.compile(r"^=== page")


def front_matter(text):
    """Returns (fields, body) for a file that opens with a YAML block, else (None, text)."""
    if text.startswith("﻿"):
        text = text[1:]
    if not text.startswith("---\n"):
        return None, text
    parts = text[4:].split("\n---", 1)
    if len(parts) < 2:
        return None, text
    fields = {}
    for line in parts[0].split("\n"):
        m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*?)\s*(?:#.*)?$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            fields[key] = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
        else:
            fields[key] = val.strip('"').strip("'")
    return fields, parts[1].lstrip("\n")


def split_body(text):
    """Returns (body, reference_block) with the <reference> block taken off the end of the body."""
    m = re.search(r"<reference>(.*?)</reference>", text, re.S)
    if not m:
        return text, None
    return text[:m.start()] + text[m.end():], m.group(1)


def paragraphs(body):
    """Prose paragraphs of a body: blank-line separated, headings and metadata lines left out."""
    out = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para or para.startswith("#") or re.match(r"^-\s+(start|end|ref_point)\s*:", para):
            continue
        out.append(re.sub(r"\s+", " ", para))
    return out


def sentences(para):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(*“])", para) if s]


def strip_quotes(text):
    """Quotations in double marks (straight or curly) replaced by a placeholder, citations kept."""
    text = re.sub(r"\"[^\"\n]*\"", "\"Q\"", text)
    return re.sub(r"“[^”\n]*”", "\"Q\"", text)


def strip_cites(text):
    return CITE.sub("", text)


def words(text):
    return len(re.findall(r"[A-Za-zÀ-ɏ][\w'À-ɏ-]*", text))


def cast_rows():
    if not os.path.exists(CAST):
        return {}
    with io.open(CAST, encoding="utf-8-sig", newline="") as fh:
        return {r["id"].strip(): r for r in csv.DictReader(fh)}


def cast_list(cell):
    return [v.strip().lower() for v in re.split(r"[;,]", cell or "") if v.strip()]


def check_prose(paras, add, kind):
    """The word, punctuation and sentence checks over a list of paragraphs."""
    for i, para in enumerate(paras, 1):
        bare = strip_cites(strip_quotes(para))
        where = f"paragraph {i}"
        if "—" in para:
            add("ERROR", where, "em-dash", para)
        if re.search(r"(?<!-)--(?!-)", para):
            add("ERROR", where, "double hyphen", para)
        if "§" in para:
            add("ERROR", where, "section sign", para)
        if "?" in bare:
            add("ERROR", where, "question mark in running prose", bare)
        for pat, label in HARD:
            for m in re.finditer(pat, bare):
                add("ERROR", where, label, bare[max(0, m.start() - 40):m.end() + 40])
        for pat, label in SOFT:
            flags = re.I if label.startswith(("account", "signal", "praise", "perception", "not-but")) else 0
            for m in re.finditer(pat, bare, flags):
                add("REVIEW", where, label, bare[max(0, m.start() - 40):m.end() + 40])
        for m in CONTACT.finditer(bare):
            if m.group(1) not in FUNCTION_WORDS:
                add("REVIEW", where, "possible contact clause: a head noun, a name and a verb with no relativiser",
                    bare[max(0, m.start() - 30):m.end() + 30])
        curly = len(CURLY.findall(para))
        if curly:
            add("REVIEW", where, f"{curly} curly quotation marks: straight marks in this project, source marks inside a quotation", "")
        dashes = len(re.findall(r"\s–\s", bare))
        if dashes > 1:
            add("ERROR", where, f"{dashes} parenthetical dashes (at most one per paragraph)", bare)
        semis, colons = bare.count(";"), bare.count(":")
        if semis > 1:
            add("ERROR", where, f"{semis} semicolons (at most one per paragraph)", bare)
        if colons > 1:
            add("ERROR", where, f"{colons} colons (at most one per paragraph)", bare)
        sents = sentences(bare)
        if sents:
            first = sents[0]
            if words(first) < 15 and re.search(r"instructiv|telling|revealing|striking|notabl|remarkabl", first, re.I):
                add("ERROR", where, "announcement opener", first)
            last = sents[-1]
            if words(last) < 10 and len(sents) > 1:
                add("REVIEW", where, "short paragraph-final sentence: justify it or fold it in", last)
        for s in sents:
            if re.search(r": [A-Z][^\"']*\.$", s) and not re.search(r"\(\w[^)]*\)\.$", s):
                add("REVIEW", where, "payoff colon: a colon introduces a quotation, a list or a definition", s)
        for m in re.finditer(r"\"([^\"\n]*)\"|“([^”\n]*)”", para):
            quoted = m.group(1) if m.group(1) is not None else m.group(2)
            if words(quoted) < 8:
                continue
            locator = r"(1\d{3}|20\d{2})[a-z]?: ?\d|section \d"
            if not re.search(locator, para[m.end():m.end() + 140]) and not re.search(locator, para[max(0, m.start() - 140):m.start()]):
                add("REVIEW", where, "sentence-length quotation without a page locator beside it", m.group(0))


def check_citations(paras, refs, add):
    entries = [e for e in re.split(r"\n\s*\n", refs or "") if e.strip()]
    for i, para in enumerate(paras, 1):
        pairs = []
        for m in CITE.finditer(para):
            for part in m.group(1).split(";"):
                # a passage taken through another author resolves through the work that carries it
                carried = re.split(r"(?:quoted|reported|cited) in ", part)
                part = carried[-1]
                y = CITE_YEAR.search(part)
                if not y:
                    continue
                names = [w for w in re.findall(r"\b[A-Z][\w'-]+", part[:y.start()]) if w not in ("And", "Et", "Al")]
                if names:
                    pairs.append((names[0], y.group(0), part.strip()))
        for m in NAMED_CITE.finditer(para):
            pairs.append((m.group(1), m.group(2), m.group(0)))
        for name, year, shown in pairs:
            if not any(name in e and year in e for e in entries):
                add("ERROR", f"paragraph {i}", "citation with no entry in the reference block", shown)


def check_bio(path, fields, body, refs, cast, add):
    stem = os.path.splitext(os.path.basename(path))[0]
    for key in ("id", "author", "author_long", "birth", "death", "pob", "pod", "period", "tags", "status"):
        if key not in fields:
            add("ERROR", "front matter", f"missing field {key}", "")
    if fields.get("id") != stem:
        add("ERROR", "front matter", "id differs from the file name", str(fields.get("id")))
    for key in ("birth", "death"):
        v = fields.get(key, "")
        if v and not re.match(r"^\d{4}(-\d{2}(-\d{2})?)?$", v):
            add("ERROR", "front matter", f"{key} is not YYYY, YYYY-MM or YYYY-MM-DD", v)
    period, tags = fields.get("period", []), fields.get("tags", [])
    if not isinstance(period, list) or not period or not set(period) <= PERIODS:
        add("ERROR", "front matter", "period empty or outside the vocabulary", str(period))
    if not isinstance(tags, list) or not tags or not set(tags) <= TAGS:
        add("ERROR", "front matter", "tags empty or outside the vocabulary", str(tags))
    if fields.get("status") not in ("draft", "reviewed"):
        add("ERROR", "front matter", "status is not draft or reviewed", str(fields.get("status")))
    row = cast.get(stem)
    if row is None:
        add("REVIEW", "front matter", "no row in the cast file", stem)
    else:
        if isinstance(period, list) and period != cast_list(row.get("periods")):
            add("ERROR", "front matter", "period differs from the cast file", f"{period} vs {cast_list(row.get('periods'))}")
        if isinstance(tags, list) and tags != cast_list(row.get("tags")):
            add("ERROR", "front matter", "tags differ from the cast file", f"{tags} vs {cast_list(row.get('tags'))}")
    paras = paragraphs(body)
    n = words(strip_cites(" ".join(paras)))
    lo, hi = SIZES["bio"]
    if not lo <= n <= hi:
        add("REVIEW", "body", f"{n} words, outside the usual {lo} to {hi}: judge whether the person requires it", "")
    if refs is None:
        add("ERROR", "body", "no <reference> block", "")
    if paras and isinstance(tags, list) and tags:
        if not any(re.search(r"\b" + t + r"\b", paras[-1], re.I) for t in tags):
            add("ERROR", "last paragraph", "does not name the person's tradition or traditions", ", ".join(tags))
    check_prose(paras, add, "bio")
    check_citations(paras, refs, add)
    return n


def check_works(path, fields, body, refs, add):
    stem = os.path.splitext(os.path.basename(path))[0]
    for key in ("author", "author_id", "orig_title", "pub_date", "orig_language", "posthumous"):
        if key not in fields:
            add("ERROR", "front matter", f"missing field {key}", "")
    aid, year = fields.get("author_id", ""), str(fields.get("pub_date", ""))
    if not re.match(r"^\d{4}$", year):
        add("ERROR", "front matter", "pub_date is not a four-digit year", year)
    # Files written since September 2026 are named <author_id>_<pub_date>-<slug>; the older
    # files carry <author_id>_<slug> without a year, which the build does not mind
    named = re.match(re.escape(aid) + r"_(\d{4})-", stem)
    if named and named.group(1) != year:
        add("ERROR", "front matter", "the year in the file name differs from pub_date", f"{stem} vs {year}")
    elif not stem.startswith(aid + "_"):
        add("ERROR", "front matter", "file name does not begin with <author_id>_", stem)
    elif not named:
        add("REVIEW", "front matter", "older file name without a year: <author_id>_<pub_date>-<slug> is the current form", stem)
    if str(fields.get("posthumous", "")).lower() not in ("true", "false"):
        add("ERROR", "front matter", "posthumous is not true or false", str(fields.get("posthumous")))
    bio = os.path.join(HERE, "author_bios", aid + ".md")
    if not os.path.exists(bio):
        add("ERROR", "front matter", "no biography for author_id", aid)
    else:
        bf, _ = front_matter(io.open(bio, encoding="utf-8").read())
        if bf and bf.get("author") != fields.get("author"):
            add("ERROR", "front matter", "author differs from the biography", f"{fields.get('author')} vs {bf.get('author')}")
        if bf and bf.get("death") and year and bf["death"][:4] < year and str(fields.get("posthumous", "")).lower() != "true":
            add("ERROR", "front matter", "published after the author's death but posthumous is not true", f"{year} after {bf['death']}")
    paras = paragraphs(body)
    n = words(strip_cites(" ".join(paras)))
    lo, hi = SIZES["works"]
    if not lo <= n <= hi:
        add("REVIEW", "body", f"{n} words, outside the usual {lo} to {hi}: judge whether the work requires it", "")
    if refs is None:
        add("ERROR", "body", "no <reference> block", "")
    check_prose(paras, add, "works")
    check_citations(paras, refs, add)
    return n


def check_cards(path, text, add):
    total = 0
    for card in re.split(r"(?m)^(?=## )", text):
        if not card.startswith("## "):
            continue
        title = card.split("\n", 1)[0][3:].strip()
        body, refs = split_body(card)
        paras = paragraphs(body)
        if len(paras) == 1 and "to develop" in paras[0]:
            continue
        n = words(strip_cites(" ".join(paras)))
        total += n
        lo, hi = SIZES["card"]
        if not lo <= n <= hi:
            add("REVIEW", title, f"{n} words, outside the usual {lo} to {hi}: judge whether the event requires it", "")
        if refs is None:
            add("ERROR", title, "no <reference> block", "")
        wrapped = lambda level, where, label, ctx: add(level, f"{title} / {where}", label, ctx)
        check_prose(paras, wrapped, "card")
        check_citations(paras, refs, wrapped)
    return total


def sweep(path, cast, quiet):
    text = io.open(path, encoding="utf-8").read()
    findings = []

    def add(level, where, label, ctx):
        ctx = re.sub(r"\s+", " ", ctx).strip()
        findings.append((level, where, label, ctx[:160]))

    rel = os.path.relpath(path, HERE).replace("\\", "/")
    folder = rel.split("/")[0]
    fields, rest = front_matter(text)
    for m in EDITORIAL.finditer(rest):
        add("ERROR", "anywhere", "a Zotero key or a note addressed to an editor: these belong in docs/editorial-notes/",
            rest[max(0, m.start() - 50):m.end() + 40])
    n = None
    if folder == "author_bios":
        if fields is None:
            add("ERROR", "front matter", "none found", "")
        else:
            body, refs = split_body(rest)
            n = check_bio(path, fields, body, refs, cast, add)
    elif folder == "author_works":
        if fields is None:
            add("ERROR", "front matter", "none found", "")
        else:
            body, refs = split_body(rest)
            n = check_works(path, fields, body, refs, add)
    elif folder == "revolutions":
        n = check_cards(path, rest, add)
    else:
        body, refs = split_body(rest)
        paras = paragraphs(body)
        n = words(strip_cites(" ".join(paras)))
        check_prose(paras, add, "prose")
        if refs is not None:
            check_citations(paras, refs, add)
    errors = sum(1 for f in findings if f[0] == "ERROR")
    reviews = len(findings) - errors
    size = f", {n} body words" if n is not None else ""
    print(f"{rel}: {errors} errors, {reviews} reviews{size}")
    if not quiet:
        for level, where, label, ctx in findings:
            print(f"  {level:6} {where}: {label}" + (f' | "{ctx}"' if ctx else ""))
    return errors


def new_files():
    out = subprocess.run(["git", "-C", HERE, "status", "--porcelain"], capture_output=True, text=True).stdout
    paths = []
    for line in out.splitlines():
        p = line[3:].strip().strip('"')
        if p.split("/")[0] in ("author_bios", "author_works", "revolutions") and p.endswith(".md"):
            paths.append(os.path.join(HERE, p))
    return paths


if __name__ == "__main__":
    args = sys.argv[1:]
    quiet = "--quiet" in args
    args = [a for a in args if a != "--quiet"]
    files = new_files() if "--new" in args else [os.path.abspath(a) for a in args]
    if not files:
        print(__doc__)
        sys.exit(2)
    cast = cast_rows()
    total = sum(sweep(f, cast, quiet) for f in files)
    print(f"\n{len(files)} files, {total} errors")
    sys.exit(1 if total else 0)
