"""Cut the background out of the square portraits, leaving the sitter on transparency.

The portraits that were edited by hand already have a transparent background and are left
alone: a file counts as cut when more than a fifth of its pixels are transparent. Every other
`author_photos/<id>.png` is copied once to `author_photos/uncut/<id>.png`, segmented with
rembg, and written back in place; the circular crop of the same id is deleted so that the
next build of Society500.R draws it again from the cut square.

Usage: python tools/cut_portraits.py [--model NAME] [--redo] [ID ...]
       python tools/cut_portraits.py --tighten ID [ID ...]
  --redo     cut again from the copy in uncut/ (for trying another model on a poor result)
  --tighten  no cutting: re-frame an already cut portrait whose sitter is small in the square, on
             a square a little wider than the sitter and aligned with the top of the head

The rembg models are downloaded on first use into the folder named by U2NET_HOME, which this
script points at D:\\AppData\\Local\\u2net unless the variable is already set.
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("U2NET_HOME", r"D:\AppData\Local\u2net")

from PIL import Image  # noqa: E402
from rembg import new_session, remove  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "author_photos"
UNCUT = PHOTOS / "uncut"
CIRCLES = PHOTOS / "circles"


def transparent_share(im):
    alpha = im.convert("RGBA").getchannel("A")
    hist = alpha.histogram()
    return sum(hist[:10]) / (im.width * im.height)


def tighten(square):
    im = Image.open(square).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
    if box is None:
        return
    x0, y0, x1, _ = box
    side = int((x1 - x0) * 1.15)
    left, top = (x0 + x1) // 2 - side // 2, y0 - int(side * 0.06)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im.crop((left, top, left + side, top + side)), (0, 0))
    canvas.resize(im.size).save(square, optimize=True, icc_profile=None)


def main(argv):
    model, redo, ids = "birefnet-portrait", False, []
    args = iter(argv)
    for a in args:
        if a == "--model":
            model = next(args)
        elif a == "--redo":
            redo = True
        else:
            ids.append(a)
    if "--tighten" in ids:
        for i in (i for i in ids if i != "--tighten"):
            tighten(PHOTOS / f"{i}.png")
            (CIRCLES / f"{i}.png").unlink(missing_ok=True)
            print(f"{i}: re-framed on the sitter")
        return
    UNCUT.mkdir(exist_ok=True)
    targets = [PHOTOS / f"{i}.png" for i in ids] if ids else sorted(PHOTOS.glob("*.png"))
    session = new_session(model)
    for square in targets:
        kept = UNCUT / square.name
        if redo and kept.exists():
            source = Image.open(kept)
        else:
            source = Image.open(square)
            if transparent_share(source) > 0.2:
                continue
            if not kept.exists():
                shutil.copy2(square, kept)
        cut = remove(source.convert("RGBA"), session=session, post_process_mask=True)
        cut.save(square, optimize=True, icc_profile=None)
        circle = CIRCLES / square.name
        if circle.exists():
            circle.unlink()
        print(f"{square.stem}: {transparent_share(cut):.2f} transparent")


if __name__ == "__main__":
    main(sys.argv[1:])
