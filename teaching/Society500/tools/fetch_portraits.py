"""Fetches portraits for the timeline's biographies from Wikimedia Commons, crops and greys them
to the style of the existing files in author_photos\\, and records their credits, so that every
face on the timeline can be traced to its source and re-fetched.

Usage:
    python tools\\fetch_portraits.py                 every row of SOURCES.csv whose portrait is missing
    python tools\\fetch_portraits.py khaldun sieyes  only the ids given (still skips existing files)
    python tools\\fetch_portraits.py --force [id …]  overwrite existing portraits
    python tools\\fetch_portraits.py --check         list every biography and whether it has a portrait
    python tools\\fetch_portraits.py --sources F [id …]   read rows from author_photos\\F instead of SOURCES.csv
    python tools\\fetch_portraits.py --credits-only  rebuild metadata.json and CREDITS.md from every SOURCES*.csv

Inputs and outputs, all relative to the repository root (the parent of this folder):

    author_photos\\SOURCES.csv   one row per portrait: id, commons_file, crop, note.
                                id is the biography id (author_bios\\<id>.md); commons_file is the
                                file name on Commons without the "File:" prefix; crop is blank or
                                four fractions "x,y,w,h" of the downloaded image giving the square
                                to keep (x,y the top-left corner, w and h its sides – if the box is
                                not square its shorter side is used, centred on the box); note is
                                free text carried into CREDITS.md, for example a warning that the
                                likeness is imagined.
    author_photos\\<id>.png      150 by 150 pixels, RGBA, greyscale, a head-and-shoulders crop.
                                The build makes a circular version in author_photos\\circles\\ and
                                finds the file by id, so a new file needs no other change.
    author_photos\\metadata.json what Commons returned for each fetched id (url, size, artist,
                                credit, licence, description), plus the crop used and the
                                retrieval date. Reruns merge into it rather than replace it.
    author_photos\\CREDITS.md    one line per portrait in metadata.json, regenerated on every run.

Only public-domain, CC0, CC BY and CC BY-SA files are accepted; any other licence puts the row on
the refused list printed at the end, and nothing is written for it. A blank crop takes the largest
square that fits, centred horizontally and set a little above the vertical centre of a portrait-
format image, which is where a face usually is; most paintings and engravings need a hand-set crop
to match the tight framing of the existing portraits, so run once, look at the result, and set the
fractions.

The Commons calls, the user-agent string and the licence reading follow the slide-image fetcher in
the SOC1030 teaching folder (AY-26-27\\tools\\fetch_images.py).
"""
import csv
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PHOTOS = os.path.join(ROOT, "author_photos")
BIOS = os.path.join(ROOT, "author_bios")
SOURCES = os.path.join(PHOTOS, "SOURCES.csv")
META = os.path.join(PHOTOS, "metadata.json")
CREDITS = os.path.join(PHOTOS, "CREDITS.md")

# The same user-agent as the slide-image fetcher, so that Commons sees one identifiable client
# for all of the module's teaching material.
UA = {"User-Agent": "SOC1030-slides/1.0 (cgmoreh@proton.me; teaching materials)"}
API = "https://commons.wikimedia.org/w/api.php"

# Width requested for the download. Commons renders a nearby size of its own choosing (960 for a
# request of 800) and a smaller original comes at its own size; the crop fractions in SOURCES.csv
# are independent of the width, so this only bounds the detail available before the resize.
DOWNLOAD_WIDTH = 800
# Side of the finished portrait, matching the existing files in author_photos\.
SIDE = 150
# Fraction of the spare height above an automatic square crop in a portrait-format image; 0 would
# put the square at the top edge, 0.5 in the middle.
AUTO_TOP_BIAS = 0.15


def api(params):
    url = API + "?" + urllib.parse.urlencode(dict(params, format="json"))
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").replace("\n", " ").strip()


def info(commons_file, width=DOWNLOAD_WIDTH):
    """What Commons records for one file: the rendering url at the requested width, the pixel size
    of the original, and the licence and attribution fields of its extended metadata."""
    d = api({"action": "query", "titles": "File:" + commons_file, "prop": "imageinfo",
             "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width,
             "iiextmetadatafilter": "LicenseShortName|Artist|Credit|Attribution|ImageDescription|DateTimeOriginal"})
    page = next(iter(d["query"]["pages"].values()))
    if "imageinfo" not in page:
        raise KeyError(f"no such file on Commons: {commons_file}")
    ii = page["imageinfo"][0]
    em = ii.get("extmetadata", {})
    g = lambda k: em.get(k, {}).get("value", "")
    return {"commons_file": commons_file, "page": ii.get("descriptionurl"),
            "thumb": ii.get("thumburl") or ii["url"], "mime": ii.get("mime"),
            "width": ii.get("width"), "height": ii.get("height"),
            "licence": g("LicenseShortName"), "artist": strip_html(g("Artist")),
            "credit": strip_html(g("Credit")), "attribution": strip_html(g("Attribution")),
            "description": strip_html(g("ImageDescription")), "date": strip_html(g("DateTimeOriginal"))}


def licence_ok(name):
    """True for the licences the timeline accepts: public domain, CC0, CC BY and CC BY-SA in any
    version or jurisdiction. Any NC or ND clause, and any other licence, is refused."""
    n = re.sub(r"[-_]", " ", name or "").strip().upper()
    if n.startswith("PUBLIC DOMAIN") or n == "CC0" or n.startswith("CC0 "):
        return True
    tokens = n.split()
    if tokens[:2] != ["CC", "BY"]:
        return False
    return not ({"NC", "ND"} & set(tokens))


def download(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as resp:
        return Image.open(io.BytesIO(resp.read()))


def parse_crop(text):
    """The four fractions of a crop field as floats, or None for a blank field."""
    if not (text or "").strip():
        return None
    parts = [float(p) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError(f"crop needs four fractions x,y,w,h, got {text!r}")
    return parts


def square_box(im, crop):
    """The pixel box (left, top, right, bottom) of the square to keep. A hand-set crop is clamped to
    the image and forced square on its shorter side; an automatic crop is the largest square that
    fits, centred horizontally and set towards the top of a portrait-format image."""
    W, H = im.size
    if crop is None:
        side = min(W, H)
        left = (W - side) // 2
        top = int((H - side) * AUTO_TOP_BIAS)
    else:
        x, y, w, h = crop
        bw, bh = w * W, h * H
        side = int(round(min(bw, bh)))
        left = int(round(x * W + (bw - side) / 2))
        top = int(round(y * H + (bh - side) / 2))
    side = max(1, min(side, W, H))
    left = max(0, min(left, W - side))
    top = max(0, min(top, H - side))
    return (left, top, left + side, top + side)


def make_portrait(im, crop):
    """The finished 150 by 150 greyscale RGBA portrait: transparency flattened on white, the square
    cut, the tones spread lightly, greyed, resized with Lanczos and given a light unsharp mask."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        flat = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        flat.alpha_composite(rgba)
        im = flat
    im = im.convert("RGB").crop(square_box(im, crop))
    im = ImageOps.autocontrast(im.convert("L"), cutoff=0.5)
    im = im.resize((SIDE, SIDE), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=60, threshold=2))
    return im.convert("RGBA")


def read_sources():
    if not os.path.exists(SOURCES):
        sys.exit(f"no {SOURCES}; create it with the header id,commons_file,crop,note")
    with io.open(SOURCES, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("id") or "").strip()]


def read_meta():
    if os.path.exists(META):
        with io.open(META, encoding="utf-8") as f:
            return json.load(f)
    return {}


def write_meta(meta):
    with io.open(META, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def write_credits(meta):
    """CREDITS.md regenerated from metadata.json: one line per fetched portrait, ids in order.
    Portraits that predate this tool have no entry and are not listed."""
    out = ["# Portrait credits", "",
           "Fetched from Wikimedia Commons by `tools\\fetch_portraits.py` from `author_photos\\SOURCES.csv`; "
           "the fields come from the metadata Commons records for each file. Each line gives the biography "
           "id, the Commons file, the artist or source, the licence, and the date of retrieval. Portraits "
           "that were added before this tool existed are not listed here.", ""]
    for pid in sorted(meta):
        m = meta[pid]
        source = m.get("artist") or m.get("credit") or m.get("attribution") or "source not recorded on Commons"
        note = f" {m['note'].strip()}" if m.get("note", "").strip() else ""
        out.append(f"- `{pid}` – [{m['commons_file']}]({m['page']}) – {source[:120]} – {m['licence']} – "
                   f"retrieved {m['retrieved']}.{note}")
    with io.open(CREDITS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def check():
    """Prints every biography id in author_bios\\ with the state of its portrait file."""
    ids = sorted(os.path.splitext(f)[0] for f in os.listdir(BIOS) if f.endswith(".md"))
    missing = []
    for pid in ids:
        have = os.path.exists(os.path.join(PHOTOS, pid + ".png"))
        print(f"{pid:<16} {'portrait' if have else 'MISSING'}")
        if not have:
            missing.append(pid)
    print(f"\n{len(ids) - len(missing)} of {len(ids)} biographies have a portrait; missing: "
          f"{', '.join(missing) or 'none'}")


def rebuild_credits():
    """metadata.json and CREDITS.md rebuilt from scratch: every row of every SOURCES*.csv in the photos
    folder whose portrait file exists is queried on Commons again, so that runs from several batch
    files, which may have overwritten one another's metadata, end in one complete record."""
    meta = {}
    files = sorted(f for f in os.listdir(PHOTOS) if f.startswith("SOURCES") and f.endswith(".csv"))
    today = datetime.date.today().isoformat()
    for name in files:
        with io.open(os.path.join(PHOTOS, name), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                pid = (r.get("id") or "").strip()
                commons_file = (r.get("commons_file") or "").strip()
                if not pid or not commons_file or not os.path.exists(os.path.join(PHOTOS, pid + ".png")):
                    continue
                try:
                    m = info(commons_file)
                except Exception as e:
                    print(f"FAILED   {pid}: {e}")
                    continue
                m.update({"crop": (r.get("crop") or "").strip() or "auto", "note": (r.get("note") or "").strip(),
                          "retrieved": today, "sources_file": name})
                meta[pid] = m
                print(f"credited {pid} <- {commons_file[:70]} | {m['licence']}")
                time.sleep(0.3)
    write_meta(meta)
    write_credits(meta)
    print(f"\ncredits rebuilt for {len(meta)} portraits from {len(files)} sources files")


def fetch(ids, force):
    rows = read_sources()
    by_id = {r["id"].strip(): r for r in rows}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        print("no row in SOURCES.csv for:", ", ".join(unknown))
    todo = [by_id[i] for i in ids if i in by_id] if ids else rows
    meta = read_meta()
    refused, fetched = [], []
    today = datetime.date.today().isoformat()
    for r in todo:
        pid = r["id"].strip()
        target = os.path.join(PHOTOS, pid + ".png")
        if os.path.exists(target) and not force:
            print(f"exists   {pid} (use --force to overwrite)")
            continue
        commons_file = (r.get("commons_file") or "").strip()
        if not commons_file:
            print(f"skipped  {pid}: no commons_file")
            continue
        try:
            m = info(commons_file)
        except Exception as e:
            print(f"FAILED   {pid}: {e}")
            continue
        if not licence_ok(m["licence"]):
            refused.append((pid, commons_file, m["licence"] or "no licence recorded"))
            print(f"refused  {pid}: {commons_file} is {m['licence'] or 'unlicensed'}")
            continue
        try:
            crop = parse_crop(r.get("crop"))
            im = download(m["thumb"])
        except Exception as e:
            print(f"FAILED   {pid}: {e}")
            continue
        # The source file's colour profile is dropped: a greyscale profile carried onto the RGBA
        # output makes ImageMagick warn on read, and the build treats the warning as an error
        make_portrait(im, crop).save(target, optimize=True, icc_profile=None)
        m.update({"crop": r.get("crop", "").strip() or "auto", "note": (r.get("note") or "").strip(),
                  "retrieved": today, "downloaded_size": list(im.size)})
        meta[pid] = m
        fetched.append(pid)
        print(f"fetched  {pid} <- {commons_file[:70]} | {m['licence']} | {im.size[0]}x{im.size[1]} | "
              f"crop {m['crop']}")
        time.sleep(0.5)
    write_meta(meta)
    write_credits(meta)
    print(f"\n{len(fetched)} fetched; credits written for {len(meta)} portraits")
    if refused:
        print("refused (licence not public domain, CC0, CC BY or CC BY-SA):")
        for pid, cf, lic in refused:
            print(f"  {pid}: {cf} – {lic}")
    return refused


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--sources" in args:                     # a per-batch sources file instead of SOURCES.csv
        i = args.index("--sources")
        SOURCES = args[i + 1] if os.path.isabs(args[i + 1]) else os.path.join(PHOTOS, args[i + 1])
        del args[i:i + 2]
    if "--check" in args:
        check()
        sys.exit(0)
    if "--credits-only" in args:
        rebuild_credits()
        sys.exit(0)
    force = "--force" in args
    ids = [a for a in args if not a.startswith("--")]
    os.makedirs(PHOTOS, exist_ok=True)
    sys.exit(1 if fetch(ids, force) else 0)
