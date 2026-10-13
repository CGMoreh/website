# Society500

The timeline application of *Sociology: The First 500 Years*, published at
<https://chrismoreh.com/teaching/Society500/>. This folder holds the whole project: the content, the
build script, the checks and the editor's notes. Only the built pages, their library and the portraits
reach the website.

## What is built and why it is committed

`Society500.R`, run from this folder (`Rscript Society500.R`), reads the content and writes:

- `index.html`, the landing page, which draws the six periods and carries the text of
  `info_overlay.md`;
- one page per period: `sources.html`, `origins.html`, `consolidation.html`, `crisis.html`,
  `reconstruction.html`, `decentring.html`;
- `lib/`, the Highcharts and htmlwidgets libraries that the pages load, with a copy of
  `js/soctime.js`;
- `author_photos/circles/`, the circular crops of the portraits.

These files are build output, but they are committed. The website is rendered by GitHub Actions
(`.github/workflows/deploy.yml`), which runs `quarto render` and never runs `Society500.R`, so the built
pages have to be in the repository for the render to find them. `_quarto.yml` excludes this folder from
rendering and copies only `teaching/Society500/*.html`, `lib/**`, `author_photos/*.png` and
`author_photos/circles/*.png` into `_site`. Never widen those globs to `teaching/Society500/**`: that
would publish `docs/`. The root `.gitattributes` marks the built files as generated, so that GitHub
collapses them in diffs. After any change to the content, rebuild and commit the pages with it.

## Sources

- `author_bios/` and `author_works/`: one markdown file per person and per work, with YAML front
  matter; a works file is named `<author_id>_<pub_date>-<slug>.md`.
- `revolutions/`: the political, ideational and technological event cards, one `## ` heading each.
- `info_overlay.md`: the information panel of every page, and the text of the landing page.
- `timeline.css`, `js/soctime.js`, `icons/`, `author_photos/*.png`: the look and behaviour of the pages.

Two optional front-matter fields deal with dates. `date_note`, in a biography or a works file, is a
short paragraph with its own citation that explains a date the sources give differently; the page marks
the date with an asterisk and prints the note at the foot of the dialog. `birth_event`, in a biography,
replaces "Born" in the tooltip when the date is of another event, such as a baptism.

## Not published

- `docs/`: the cast file, the editorial notes (everything removed from the public texts, and the
  decisions left to the editor), the copy-screen record and the changelog.
- `tools/`: the Python checks. `tools/sweep_prose.py` sweeps the prose rules, `tools/copy_screen.py`
  and `tools/card_screen.py` screen biographies, works and cards for text copied from their sources.
- `_validate.R`: checks the front matter against the cast file and the vocabularies.

The writing brief for the content is kept with the book project, in
`D:\ACADEMIC\PUBLICATIONS\BOOKS\2026_Society500\notes\timeline-content-instructions-2026-09-13.md`.
