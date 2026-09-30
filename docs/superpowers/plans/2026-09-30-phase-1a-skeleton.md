# LeggoLeopardi Phase 1a (Skeleton) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harvest the N35c text of all 41 Canti from WikiLeopardi into provisional TEI, and serve it as a verse reading view (Leggo, without commentaries) on an Express site deployed to Vercel.

**Architecture:** A Python pipeline (`pipeline/leggo_pipeline/`) does the following:
- fetches WikiLeopardi pages through the MediaWiki API into a local cache;
- parses the `<poem>` blocks into verses;
- writes one TEI file per poem to `tei/base/`;
- validates the TEI;
- turns it into static JSON under `public/data/`.

An Express + EJS app (`app/`) only reads that JSON, so it never needs Python or a database. GitHub Actions re-runs tests, validation and the JSON build on every push. Vercel serves the app as one serverless function, plus the static files in `public/`.

**Tech Stack:**
- Python 3.12 (managed by `uv`), lxml, requests, pytest.
- Node 22, Express 4, EJS 3, i18n 0.15, cookie-parser, node:test + supertest.
- Vercel, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`. Phase 1a is §11 item 1. It implements §4 (repo, manifest, addressing), §5.1, §5.2, §5.8, §5.9, the Leggo part of §6, §8 (Ocean v1 palette) and §9.

## Global Constraints

- **Text fidelity.** Every string taken from a source is kept character for character as the source has it (`’` stays `’`, `'` stays `'`). Never normalise Unicode (no NFC/NFD conversion). Never "correct" spelling. The only normalisation allowed is whitespace: trim line ends and collapse runs of whitespace (including `&nbsp;` used inside text) to one space.
- **Stable ids.**
  - Poem: `c{n}` (no zero padding, e.g. `c12`).
  - Verse: `c{n}.v{v}`.
  - Word: `c{n}.v{v}.w{k}`.
  - A line without a verse number after verse `v`: `c{n}.v{v}.u{j}`.
  - File names follow the same pattern: `tei/base/c12.xml`, `public/data/c12.json`.
- **No hard-coded poem lists.** Every list of poems comes from `canti.json`.
- **No LLM or paid API calls** anywhere in the pipeline.
- **Network etiquette for WikiLeopardi:**
  - API `https://wikileopardi.altervista.org/wiki_leopardi/api.php`.
  - Send a browser-like `User-Agent`; Python's default agent gets HTTP 403.
  - Wait 0.5 s between requests.
  - Cache every page under `pipeline/cache/` (gitignored). A page already in the cache is never fetched again.
- **Secrets:** `.env` is never committed. Secrets live only in the Vercel dashboard. Phase 1a needs none.
- **Python:** run everything as `cd pipeline && uv run …`, on Python 3.12, which is pinned in `pipeline/.python-version`. Never use the system `python3` (3.10).
- **Node:** 22.x. The app must not depend on the working directory: every path is built from `__dirname`.
- **Palette "Ocean v1"** (spec §8):
  - main `#2F6391`
  - dark `#0E3A62`
  - tint `#A9C8DB`
  - panels `#E6EFF6`
  - accent `#B8743A`
  - paper `#F7F4EA`
  - fonts Cormorant Garamond and Cormorant SC

  All colours are CSS custom properties in one `:root` block, so the warmer variant planned for later only needs to change that block.
- **Commits:** end each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## What the source looks like (facts established on 2026-09-30)

- **Index page:** `N35c Edizione critica` lists one entry page per poem as `* [[<page title>|<roman>. <label>]]`. That makes 41 poems once the entries for `FRONTESPIZIO`, `NOTIZIA` and `Note` are skipped.
- **Page chains:**
  - Every page links to the next one with `[[<next title>|→ …]]`, and the last such link on a page is the "next" page.
  - Following these links from each entry page gives exactly one page series per poem, which avoids the duplicate page series the wiki also contains.
  - Stop when the next page is another poem's entry page, or starts with `N35c Note`.
- **Verse lines** inside `<poem>…</poem>` look like `12 text`.
  - `&nbsp;` right after the number: **≥3** marks a new stanza, and **1–2** mark an indented verse (the terzine of *Il primo amore*).
  - A blank line before a verse, on the same page, also starts a new stanza.
- **Two verses can share one line**: `137 Al vicino ed inciampo, 138 Stolto crede…` in *La ginestra*.
- **Genuine gap:** *Consalvo* v.130 is missing in the source. Report it; never invent it.
- **Lines without a verse number:**
  - Before verse 1 they are title lines, epigraphs with their attribution, or a speaker name.
  - After verse 1 they are speaker names in ALL CAPS (`MELISSO.`) or split half-verses (`Egli ci ha tante stelle,`).
  - Stray `←`/`→` navigation lines also appear and are dropped.
- **Markup inside `<poem>`:**
  - `<span style=…>`/`</span>` is highlighting. Highlighted links mark variant loci; their targets are needed in phase 1b.
  - `[[target|shown]]` and `[[target]]` links display the `shown` or `target` text.
  - `&nbsp;`.
  - `<small>`/`</small>`.
  - `''…''` marks italics.
  - Links to `N35c Note p. …` are author-note calls such as `(12)`.
- **Fixtures** (already in the repo): `pipeline/tests/fixtures/n35c_infinito_p62.wiki` and `pipeline/tests/fixtures/n35c_index.wiki` are the real wikitext.
- **Vignette:** `public/img/vignette-n35c-infinito.jpg` is already in the repo.

## Review Focus

1. **The wiki changes.** A page in a chain is deleted, renamed, or loops back. The harvester must stop with an error that names the poem, and must never write a silently truncated poem. Tests: Task 4.
2. **Duplicate or out-of-order verse numbers** (the wiki has duplicate page series). They must be reported and dropped, not rendered twice. Tests: Task 3.
3. **Accents and apostrophes** (`lúgubri`, `dì`, `’` vs `'`, and NFD input). The written TEI must contain exactly the input characters. Tests: Task 6.
4. **Bad poem addresses** (`/leggo/0`, `/leggo/42`, `/leggo/abc`, `/leggo/01`). They return 404, never 500. The poem selector redirect only goes to a known poem. Tests: Task 10.
5. **Running from a different working directory or as a Vercel function.** Data, views and locales must still be found. Tests: Task 9 (chdir before require); deployment check: Task 12.

---

## File Structure

```
.gitignore                      (exists)
README.md                       what the project is, how to build and run
CLAUDE.md                       conventions for future sessions (fidelity, ids, no LLM)
canti.json                      manifest, generated by Task 5, then hand-reviewed
pipeline/
  pyproject.toml, .python-version, uv.lock
  schema/tei_all.rng            copied from ../LeopardiTEIConversion/tei_all.rng
  leggo_pipeline/
    __init__.py
    paths.py                    absolute paths of repo folders
    wikitext.py                 wikitext → verses (clean_inline, parse_pages)
    tokens.py                   verse text → w / pc / ref tokens
    harvest.py                  WikiClient (cache + HTTP), parse_index, follow_chain
    manifest.py                 build / merge / load canti.json
    build_base.py               ParsedPoem → TEI; writes tei/base, work/loci, reports
    validate.py                 schema + id + numbering checks
    build_site_data.py          TEI → public/data/*.json
  tests/
    fixtures/                   (exists) real wikitext
    test_wikitext.py, test_tokens.py, test_harvest.py, test_manifest.py,
    test_build_base.py, test_validate.py, test_build_site_data.py
  work/loci/c{n}.json           variant loci for phase 1b (generated, committed)
tei/base/c{n}.xml               generated, committed
reports/base_report.md          generated, committed
public/
  img/vignette-n35c-infinito.jpg  (exists)
  css/site.css
  data/index.json, c{n}.json    generated, committed
package.json, package-lock.json
app/
  app.js                        Express app (exported, no listen)
  server.js                     local server
  data.js                       reads public/data
  locales/it.json, en.json
  views/partials/{head,nav,footer}.ejs, home.ejs, leggo.ejs, 404.ejs
  tests/app.test.js
api/index.js                    Vercel entry: re-exports app
vercel.json
.github/workflows/build.yml
```

---

### Task 1: Pipeline scaffold, repo docs, schema

**Files:**
- Create: `pipeline/pyproject.toml`, `pipeline/.python-version`
- Create: `pipeline/leggo_pipeline/__init__.py`, `pipeline/leggo_pipeline/paths.py`
- Create: `pipeline/schema/tei_all.rng`, copied from `../LeopardiTEIConversion/tei_all.rng`
- Create: `README.md`, `CLAUDE.md`
- Test: `pipeline/tests/test_paths.py`

**Interfaces:**
- Produces: `leggo_pipeline.paths` with the `Path` constants `ROOT, CANTI, TEI_BASE, CACHE, LOCI, SCHEMA, DATA, REPORTS`.

- [ ] **Step 1: Create `pipeline/pyproject.toml`**

```toml
[project]
name = "leggo-pipeline"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["lxml>=5.2", "requests>=2.32"]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["leggo_pipeline"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Pin Python, create the package, copy the schema**

```bash
cd pipeline
uv python pin 3.12
mkdir -p leggo_pipeline schema
touch leggo_pipeline/__init__.py
cp ../../LeopardiTEIConversion/tei_all.rng schema/tei_all.rng
uv sync
```

Expected: `.python-version` contains `3.12`, a `.venv/` is created, and `uv.lock` is written.

- [ ] **Step 3: Write the failing test `pipeline/tests/test_paths.py`**

```python
from leggo_pipeline import paths


def test_root_is_repo_root():
    assert (paths.ROOT / "pipeline" / "pyproject.toml").is_file()
    assert paths.CANTI == paths.ROOT / "canti.json"
    assert paths.TEI_BASE == paths.ROOT / "tei" / "base"
    assert paths.SCHEMA.is_file()
```

- [ ] **Step 4: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_paths.py -q`
Expected: FAIL, `ImportError: cannot import name 'paths'`.

- [ ] **Step 5: Write `pipeline/leggo_pipeline/paths.py`**

```python
"""Absolute paths of the repository folders used by the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANTI = ROOT / "canti.json"
TEI_BASE = ROOT / "tei" / "base"
CACHE = ROOT / "pipeline" / "cache"
LOCI = ROOT / "pipeline" / "work" / "loci"
SCHEMA = ROOT / "pipeline" / "schema" / "tei_all.rng"
DATA = ROOT / "public" / "data"
REPORTS = ROOT / "reports"
```

- [ ] **Step 6: Run it and see it pass**

Run: `cd pipeline && uv run pytest tests/test_paths.py -q`
Expected: `1 passed`.

- [ ] **Step 7: Write `README.md`**

```markdown
# LeggoLeopardi

Digital edition of Giacomo Leopardi's *Canti* (DH.ARC, Università di Bologna), sister project of LeggoManzoni.
Reading text: N35c (the corrected copy of *Canti*, Napoli, Starita 1835). Current transcription: WikiLeopardi, provisional.

## Build the data (Python 3.12 via uv)

    cd pipeline
    uv run python -m leggo_pipeline.manifest          # (re)build canti.json from WikiLeopardi
    uv run python -m leggo_pipeline.build_base        # tei/base/*.xml + reports/base_report.md
    uv run python -m leggo_pipeline.validate          # TEI checks
    uv run python -m leggo_pipeline.build_site_data   # public/data/*.json
    uv run pytest

## Run the site (Node 22)

    npm install
    npm run dev        # http://localhost:8000
    npm test

Design spec: `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`.
```

- [ ] **Step 8: Write `CLAUDE.md`**

```markdown
# LeggoLeopardi: conventions

- Texts are kept character for character as in the source: never change `’`/`'`, accents, spelling or endings; never normalise Unicode. The only allowed normalisation is trimming/collapsing whitespace.
- Ids never change once published: `c{n}`, `c{n}.v{v}`, `c{n}.v{v}.w{k}`, `c{n}.v{v}.u{j}`. Commentaries and translations point at them.
- Every list of poems comes from `canti.json`; never hard-code poem numbers or titles.
- The pipeline makes no LLM or paid API calls unless the user approves the cost first.
- WikiLeopardi: cache every page in `pipeline/cache/`, browser-like User-Agent, 0.5 s between requests.
- Python: `cd pipeline && uv run …` (3.12). Node 22. The app never reads files relative to the working directory.
- `public/data/` and `tei/base/` are generated: change the pipeline, not the output.
- Spec: `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`. Plans: `docs/superpowers/plans/`.
```

- [ ] **Step 9: Commit**

```bash
git add README.md CLAUDE.md pipeline/pyproject.toml pipeline/.python-version pipeline/uv.lock pipeline/leggo_pipeline pipeline/schema pipeline/tests/test_paths.py pipeline/tests/fixtures public/img
git commit -m "Scaffold the Python pipeline, repo docs and TEI schema

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Inline wikitext cleaning (`clean_inline`)

**Files:**
- Create: `pipeline/leggo_pipeline/wikitext.py` (this task writes the whole module except `parse_pages`, which Task 3 adds)
- Test: `pipeline/tests/test_wikitext.py`

**Interfaces:**
- Produces:
  - `Span(start: int, end: int, target: str = "")`. Offsets index into the cleaned text; `end` is exclusive.
  - `Cleaned(text: str, italic: list[Span], loci: list[Span], notes: list[Span])`.
  - `clean_inline(raw: str) -> Cleaned`.

- [ ] **Step 1: Write the failing tests in `pipeline/tests/test_wikitext.py`**

```python
from leggo_pipeline.wikitext import clean_inline


def test_highlight_and_piped_link_show_displayed_text():
    raw = '<span style="background-color:yellow;">[[Dell\'ultimo|Dell\']]</span>ultimo orizzonte il guardo esclude.'
    c = clean_inline(raw)
    assert c.text == "Dell'ultimo orizzonte il guardo esclude."
    assert len(c.loci) == 1
    assert c.loci[0].target == "Dell'ultimo"
    assert c.text[c.loci[0].start : c.loci[0].end] == "Dell'"


def test_plain_link_and_trailing_space():
    c = clean_inline('<span style="background-color:yellow;">[[Immensità]]</span> s’annega il pensier mio: ')
    assert c.text == "Immensità s’annega il pensier mio:"
    assert c.text[c.loci[0].start : c.loci[0].end] == "Immensità"


def test_italic_inside_link_and_note_call():
    c = clean_inline('<span style="background-color:yellow;">[[Nè ... danzerà|D\'un \'\'walser\'\' danzerà]]</span>. Tanto la possa')
    assert c.text == "D'un walser danzerà. Tanto la possa"
    assert [c.text[s.start : s.end] for s in c.italic] == ["walser"]

    c = clean_inline("''Le magnifiche sorti e progressive'' ([[N35c Note p. 176|12]]).")
    assert c.text == "Le magnifiche sorti e progressive (12)."
    assert [c.text[s.start : s.end] for s in c.italic] == ["Le magnifiche sorti e progressive"]
    assert [(c.text[s.start : s.end], s.target) for s in c.notes] == [("12", "N35c Note p. 176")]
    assert c.loci == []


def test_navigation_arrows_are_not_loci():
    c = clean_inline("[[N35c I. ǁ ALL'ITALIA. p. 7|←]] [[N35c I. ǁ ALL'ITALIA. p. 9|→]]")
    assert c.text == "← →"
    assert c.loci == []


def test_nbsp_small_and_whitespace_runs_collapse_and_spans_follow():
    c = clean_inline("<small>SOPRA</small>&nbsp;&nbsp; IL  [[RITRATTO]]")
    assert c.text == "SOPRA IL RITRATTO"
    assert c.text[c.loci[0].start : c.loci[0].end] == "RITRATTO"


def test_characters_are_never_changed():
    raw = "Ai lúgubri miei giorni, quest’ermo, l'altro, dì"
    assert clean_inline(raw).text == raw
    nfd = "dì"  # decomposed "dì" must stay decomposed
    assert clean_inline(nfd).text == nfd
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd pipeline && uv run pytest tests/test_wikitext.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'leggo_pipeline.wikitext'`.

- [ ] **Step 3: Write `pipeline/leggo_pipeline/wikitext.py`**

```python
"""Parse WikiLeopardi <poem> blocks into verses, keeping the text exactly."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

LINK = re.compile(r"\[\[(?P<target>[^\]|]+?)(?:\|(?P<shown>[^\]]*))?\]\]", re.S)
INLINE = re.compile(
    r"\[\[(?P<target>[^\]|]+?)(?:\|(?P<shown>[^\]]*))?\]\]"
    r"|<span[^>]*>|</span>|</?small>|&nbsp;|''",
    re.S,
)
POEM = re.compile(r"<poem>(.*?)</poem>", re.S)
VERSE = re.compile(r"^(\d+)((?:&nbsp;|\s)*)(.*)$", re.S)
ARROWS_ONLY = re.compile(r"^[\s←→]*$")
SPEAKER = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ’' ]*\.$")
NOTE_PREFIX = "N35c Note"


@dataclass
class Span:
    start: int
    end: int
    target: str = ""


@dataclass
class Cleaned:
    text: str
    italic: list[Span] = field(default_factory=list)
    loci: list[Span] = field(default_factory=list)
    notes: list[Span] = field(default_factory=list)


def _squeeze(c: Cleaned) -> Cleaned:
    """Trim the ends and collapse whitespace runs to one space, remapping every span."""
    text = c.text
    keep: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        is_space = ch.isspace()
        if is_space and prev_space:
            continue
        keep.append(i)
        prev_space = is_space
    while keep and text[keep[-1]].isspace():
        keep.pop()
    new = "".join(" " if text[i].isspace() else text[i] for i in keep)

    def fix(spans: list[Span]) -> list[Span]:
        return [
            Span(bisect.bisect_left(keep, s.start), bisect.bisect_left(keep, s.end), s.target)
            for s in spans
        ]

    return Cleaned(new, fix(c.italic), fix(c.loci), fix(c.notes))


def clean_inline(raw: str) -> Cleaned:
    """Remove wiki markup from one line; record italic, variant-locus and note-call spans."""
    parts: list[str] = []
    italic: list[Span] = []
    loci: list[Span] = []
    notes: list[Span] = []
    open_italic: int | None = None
    pos = 0

    def length() -> int:
        return sum(len(p) for p in parts)

    for m in INLINE.finditer(raw):
        parts.append(raw[pos : m.start()])
        pos = m.end()
        token = m.group(0)
        if m.group("target") is not None:
            target = m.group("target").strip()
            shown = m.group("shown")
            inner = clean_inline(m.group("target") if shown is None else shown)
            start = length()
            parts.append(inner.text)
            italic += [Span(start + s.start, start + s.end) for s in inner.italic]
            end = length()
            if target.startswith(NOTE_PREFIX):
                notes.append(Span(start, end, target))
            elif not ARROWS_ONLY.match(inner.text):
                loci.append(Span(start, end, target))
        elif token == "&nbsp;":
            parts.append(" ")
        elif token == "''":
            if open_italic is None:
                open_italic = length()
            else:
                italic.append(Span(open_italic, length()))
                open_italic = None
    parts.append(raw[pos:])
    return _squeeze(Cleaned("".join(parts), italic, loci, notes))
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `cd pipeline && uv run pytest tests/test_wikitext.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/leggo_pipeline/wikitext.py pipeline/tests/test_wikitext.py
git commit -m "Clean WikiLeopardi inline markup while keeping the text exact

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Poem parsing (`parse_pages`)

**Files:**
- Modify: `pipeline/leggo_pipeline/wikitext.py` (append the code below)
- Test: `pipeline/tests/test_wikitext.py` (append the tests below)

**Interfaces:**
- Consumes: `clean_inline`, `Span`, and the regexes `LINK, POEM, VERSE, ARROWS_ONLY, SPEAKER` from Task 2.
- Produces:
  - `Line(kind: str, text: str, n: int | None = None, stanza_start: bool = False, indent: int = 0, italic: list[Span], loci: list[Span], notes: list[Span], page: str = "")`. `kind` is `"verse"`, `"label"` (speaker, ALL CAPS) or `"unnumbered"`.
  - `ParsedPoem(pre: list[str], lines: list[Line], missing: list[int], problems: list[str])`. `pre` holds the unnumbered lines before verse 1.
  - `parse_pages(pages: list[tuple[str, str]]) -> ParsedPoem`, where `pages` is an ordered list of `(page title, wikitext)`.

- [ ] **Step 1: Append the failing tests to `pipeline/tests/test_wikitext.py`**

```python
from pathlib import Path

from leggo_pipeline.wikitext import parse_pages

FIXTURES = Path(__file__).parent / "fixtures"

INFINITO = [
    "Sempre caro mi fu quest’ermo colle,",
    "E questa siepe, che da tanta parte",
    "Dell'ultimo orizzonte il guardo esclude.",
    "Ma sedendo e mirando, interminati",
    "Spazi di là da quella, e sovrumani",
    "Silenzi, e profondissima quiete",
    "Io nel pensier mi fingo; ove per poco",
    "Il cor non si spaura. E come il vento",
    "Odo stormir tra queste piante, io quello",
    "Infinito silenzio a questa voce",
    "Vo comparando: e mi sovvien l’eterno,",
    "E le morte stagioni, e la presente",
    "E viva, e il suon di lei. Così tra questa",
    "Immensità s’annega il pensier mio:",
    "E il naufragar m’è dolce in questo mare.",
]


def _infinito():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    return parse_pages([("N35c XII. ‖ L'INFINITO. p. 62", text)])


def test_infinito_real_page():
    p = _infinito()
    assert p.pre == ["XII.", "L'INFINITO."]
    verses = [l for l in p.lines if l.kind == "verse"]
    assert [l.n for l in verses] == list(range(1, 16))
    assert [l.text for l in verses] == INFINITO
    assert sum(l.stanza_start for l in verses) == 1
    assert p.missing == [] and p.problems == []


def test_infinito_variant_loci():
    v = {l.n: l for l in _infinito().lines}
    assert [(s.target, v[4].text[s.start : s.end]) for s in v[4].loci] == [("interminati ‖ Spazi", "interminati")]
    assert [(s.target, v[5].text[s.start : s.end]) for s in v[5].loci] == [("interminati ‖ Spazi", "Spazi")]
    assert [(s.target, v[13].text[s.start : s.end]) for s in v[13].loci] == [("il suon", "il")]


def _page(body: str) -> str:
    return f"[[prev|←]] [[next|→]]\n<poem>\n{body}\n</poem>\n"


def test_stanzas_indent_blank_lines_and_page_breaks():
    p1 = _page(
        "X.\n[[Titolo: PROVA.|PROVA.]]\n\n"
        "1 Primo\n2 &nbsp;&nbsp;Secondo rientrato\n3 Terzo\n\n\n"
        "4&nbsp;&nbsp;&nbsp;&nbsp; Quarto nuova strofa\n5 Quinto\n\n"
    )
    p2 = _page("6 Sesto, stessa strofa dopo il cambio pagina\n\n7 Settimo dopo riga vuota")
    p = parse_pages([("p1", p1), ("p2", p2)])
    v = {l.n: l for l in p.lines}
    assert p.pre == ["X.", "PROVA."]
    assert [n for n, l in v.items() if l.stanza_start] == [1, 4, 7]
    assert v[2].indent == 2 and v[1].indent == 0 and v[4].indent == 0


def test_two_verses_on_one_line_are_split():
    p = parse_pages([("p", _page("136 Uno,\n137 Al vicino ed inciampo, 138 Stolto crede così qual fora in campo "))])
    v = {l.n: l.text for l in p.lines}
    assert v[137] == "Al vicino ed inciampo,"
    assert v[138] == "Stolto crede così qual fora in campo"
    assert p.missing == list(range(1, 136))


def test_gap_is_reported_not_invented():
    p = parse_pages([("N35c XVII. Consalvo p. 80", _page("1 a\n2 b\n4 d"))])
    assert [l.n for l in p.lines] == [1, 2, 4]
    assert p.missing == [3]
    assert p.problems == ["N35c XVII. Consalvo p. 80: verse(s) 3-3 missing in source"]


def test_duplicate_and_out_of_order_verses_are_dropped_and_reported():
    p = parse_pages([("p84", _page("1 a\n2 b")), ("p84bis", _page("2 b again\n3 c"))])
    assert [(l.n, l.text) for l in p.lines] == [(1, "a"), (2, "b"), (3, "c")]
    assert p.problems == ["p84bis: verse 2 after verse 2 (duplicate or out of order), dropped"]


def test_speakers_and_unnumbered_lines_after_verse_one():
    p = parse_pages([("p", _page("XXXVII.\nALCETA.\n1 Odi, Melisso\nMELISSO.\nEgli ci ha tante stelle,\n2 Che"))])
    assert p.pre == ["XXXVII.", "ALCETA."]
    assert [(l.kind, l.text) for l in p.lines] == [
        ("verse", "Odi, Melisso"),
        ("label", "MELISSO."),
        ("unnumbered", "Egli ci ha tante stelle,"),
        ("verse", "Che"),
    ]
    assert p.problems == ["p: line without verse number after verse 1: 'Egli ci ha tante stelle,'"]


def test_navigation_lines_inside_poem_are_dropped():
    p = parse_pages([("p", _page("1 a\n[[N35c X p. 7|←]] [[N35c X p. 9|→]]\n2 b"))])
    assert [l.kind for l in p.lines] == ["verse", "verse"]


def test_no_verses_is_a_problem():
    assert parse_pages([("p", "no poem here")]).problems == ["no verses found"]
```

Note: in `test_two_verses_on_one_line_are_split`, verses 1–135 are absent from that synthetic page, so they are reported missing. The assertion checks exactly that list.

- [ ] **Step 2: Run them and see them fail**

Run: `cd pipeline && uv run pytest tests/test_wikitext.py -q`
Expected: FAIL, `ImportError: cannot import name 'parse_pages'`.

- [ ] **Step 3: Append this to `pipeline/leggo_pipeline/wikitext.py`**

```python
@dataclass
class Line:
    kind: str  # "verse", "label" (speaker) or "unnumbered"
    text: str
    n: int | None = None
    stanza_start: bool = False
    indent: int = 0
    italic: list[Span] = field(default_factory=list)
    loci: list[Span] = field(default_factory=list)
    notes: list[Span] = field(default_factory=list)
    page: str = ""


@dataclass
class ParsedPoem:
    pre: list[str] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _join_multiline_links(block: str) -> str:
    return LINK.sub(lambda m: m.group(0).replace("\n", " "), block)


def _split_run_on(n: int, rest: str) -> list[tuple[int, str]]:
    """'137 A, 138 B' arrives as n=137, rest='A, 138 B': split at the next expected number."""
    out: list[tuple[int, str]] = []
    while True:
        m = re.search(rf"\s{n + 1}\s", rest)
        if not m:
            break
        out.append((n, rest[: m.start()]))
        n, rest = n + 1, rest[m.end() :]
    out.append((n, rest))
    return out


def parse_pages(pages: list[tuple[str, str]]) -> ParsedPoem:
    """Parse the ordered (title, wikitext) pages of one poem."""
    poem = ParsedPoem()
    last = 0
    for title, wikitext in pages:
        for block in POEM.findall(wikitext):
            blank_before = False
            seen_in_block = False
            for raw in _join_multiline_links(block).split("\n"):
                raw = raw.strip()
                if not raw:
                    blank_before = True
                    continue
                m = VERSE.match(raw)
                if m:
                    nbsp = m.group(2).count("&nbsp;")
                    for i, (n, rest) in enumerate(_split_run_on(int(m.group(1)), m.group(3))):
                        if n <= last:
                            poem.problems.append(
                                f"{title}: verse {n} after verse {last} (duplicate or out of order), dropped"
                            )
                            continue
                        if n > last + 1:
                            gap = list(range(last + 1, n))
                            poem.missing += gap
                            poem.problems.append(f"{title}: verse(s) {gap[0]}-{gap[-1]} missing in source")
                        first_part = i == 0
                        c = clean_inline(rest)
                        poem.lines.append(
                            Line(
                                "verse",
                                c.text,
                                n,
                                stanza_start=last == 0
                                or (first_part and (nbsp >= 3 or (blank_before and seen_in_block))),
                                indent=nbsp if first_part and nbsp < 3 else 0,
                                italic=c.italic,
                                loci=c.loci,
                                notes=c.notes,
                                page=title,
                            )
                        )
                        last = n
                    seen_in_block = True
                    blank_before = False
                    continue
                c = clean_inline(raw)
                if not c.text or ARROWS_ONLY.match(c.text):
                    continue
                if last == 0:
                    poem.pre.append(c.text)
                elif SPEAKER.match(c.text):
                    poem.lines.append(Line("label", c.text, page=title))
                else:
                    poem.lines.append(
                        Line("unnumbered", c.text, italic=c.italic, loci=c.loci, notes=c.notes, page=title)
                    )
                    poem.problems.append(f"{title}: line without verse number after verse {last}: {c.text!r}")
                seen_in_block = True
                blank_before = False
    if last == 0:
        poem.problems.append("no verses found")
    return poem
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `cd pipeline && uv run pytest tests/test_wikitext.py -q`
Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/leggo_pipeline/wikitext.py pipeline/tests/test_wikitext.py
git commit -m "Parse WikiLeopardi poem pages into numbered verses and stanzas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Tokenizer and harvester

These two small modules come in one task because the harvester's output is only useful once it can be parsed. Each module has its own tests.

**Files:**
- Create: `pipeline/leggo_pipeline/tokens.py`, `pipeline/leggo_pipeline/harvest.py`
- Test: `pipeline/tests/test_tokens.py`, `pipeline/tests/test_harvest.py`

**Interfaces:**
- Consumes: `Span` (Task 2).
- Produces:
  - `Token(text: str, kind: str, start: int, end: int, italic: bool = False)`, where `kind` is `"w"`, `"pc"` or `"ref"`.
  - `tokenize(text: str, italic: list[Span] = (), notes: list[Span] = ()) -> list[Token]`.
  - `INDEX_TITLE = "N35c Edizione critica"`.
  - `WikiClient(cache_dir: Path, fetch: Callable[[str], str | None] | None = None, delay: float = 0.5)` with `.page(title) -> str`. It raises `PageMissing` when the page doesn't exist.
  - `parse_index(wikitext: str) -> list[tuple[str, str]]`, returning `(entry_page, label)` pairs.
  - `next_page(wikitext: str) -> str | None`.
  - `follow_chain(client, entry: str, stop: set[str], max_pages: int = 30) -> list[str]`. It raises `ChainError`.

- [ ] **Step 1: Write the failing `pipeline/tests/test_tokens.py`**

```python
from leggo_pipeline.tokens import tokenize
from leggo_pipeline.wikitext import Span


def kinds(text, **kw):
    return [(t.text, t.kind) for t in tokenize(text, **kw)]


def test_words_elisions_punctuation():
    assert kinds("Sempre caro mi fu quest’ermo colle,") == [
        ("Sempre", "w"), ("caro", "w"), ("mi", "w"), ("fu", "w"),
        ("quest’", "w"), ("ermo", "w"), ("colle", "w"), (",", "pc"),
    ]
    assert kinds("Dell'ultimo") == [("Dell'", "w"), ("ultimo", "w")]
    assert kinds("e ’l cor") == [("e", "w"), ("’l", "w"), ("cor", "w")]
    assert kinds("dì, lúgubri!") == [("dì", "w"), (",", "pc"), ("lúgubri", "w"), ("!", "pc")]


def test_offsets_rebuild_the_text():
    text = "Vo comparando: e mi sovvien l’eterno,"
    toks = tokenize(text)
    assert all(text[t.start : t.end] == t.text for t in toks)


def test_note_calls_and_italics():
    text = "progressive (12)."
    toks = tokenize(text, notes=[Span(13, 15, "N35c Note p. 176")], italic=[Span(0, 11)])
    assert [(t.text, t.kind, t.italic) for t in toks] == [
        ("progressive", "w", True), ("(", "pc", False), ("12", "ref", False), (")", "pc", False), (".", "pc", False),
    ]
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_tokens.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/leggo_pipeline/tokens.py`**

```python
"""Split a verse into words (w), punctuation (pc) and author-note calls (ref)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .wikitext import Span

# A word may end with an elision apostrophe (quest’, Dell'); a word may start with one (’l).
TOKEN = re.compile(r"[^\W\d_]+['’]?|['’][^\W\d_]+|\d+|[^\w\s]")


@dataclass
class Token:
    text: str
    kind: str  # "w", "pc" or "ref"
    start: int
    end: int
    italic: bool = False


def _inside(start: int, end: int, spans) -> bool:
    return any(s.start <= start and end <= s.end for s in spans)


def tokenize(text: str, italic: list[Span] = (), notes: list[Span] = ()) -> list[Token]:
    tokens: list[Token] = []
    for m in TOKEN.finditer(text):
        s, e, t = m.start(), m.end(), m.group(0)
        if _inside(s, e, notes):
            kind = "ref"
        elif t[0].isalnum() or (t[0] in "'’" and len(t) > 1):
            kind = "w"
        else:
            kind = "pc"
        tokens.append(Token(t, kind, s, e, italic=_inside(s, e, italic)))
    return tokens
```

- [ ] **Step 4: Run it and see it pass**

Run: `cd pipeline && uv run pytest tests/test_tokens.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Write the failing `pipeline/tests/test_harvest.py`**

```python
from pathlib import Path

import pytest

from leggo_pipeline.harvest import ChainError, PageMissing, WikiClient, follow_chain, next_page, parse_index

FIXTURES = Path(__file__).parent / "fixtures"


def fake_client(tmp_path, pages):
    calls = []

    def fetch(title):
        calls.append(title)
        return pages.get(title)

    return WikiClient(tmp_path, fetch=fetch, delay=0), calls


def test_parse_index_real_fixture():
    entries = parse_index((FIXTURES / "n35c_index.wiki").read_text(encoding="utf-8"))
    assert len(entries) == 41
    assert entries[0] == ("N35c I. ǁ ALL'ITALIA. p. 7", "I. All'Italia")
    assert entries[11] == ("N35c XII. ‖ L'INFINITO. p. 62", "XII. L'infinito")
    assert entries[-1] == ("N35c XLI. Dello stesso p. 169", "XLI. Dello stesso")


def test_next_page_uses_last_forward_link():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    assert next_page(text) == "N35c XIII. La sera del dì di festa p. 63"
    assert next_page("no links") is None


def test_client_caches_pages(tmp_path):
    client, calls = fake_client(tmp_path, {"A": "text of A"})
    assert client.page("A") == "text of A"
    assert client.page("A") == "text of A"
    assert calls == ["A"]
    again, calls2 = fake_client(tmp_path, {})
    assert again.page("A") == "text of A" and calls2 == []


def test_missing_page_raises(tmp_path):
    client, _ = fake_client(tmp_path, {})
    with pytest.raises(PageMissing):
        client.page("Nope")


def test_follow_chain_stops_at_next_poem_and_notes(tmp_path):
    pages = {
        "P1 a": "[[P1 b|→]]",
        "P1 b": "[[P2 a|→]]",
        "P2 a": "[[N35c Note p. 171|→]]",
    }
    client, _ = fake_client(tmp_path, pages)
    assert follow_chain(client, "P1 a", stop={"P1 a", "P2 a"}) == ["P1 a", "P1 b"]
    assert follow_chain(client, "P2 a", stop={"P1 a", "P2 a"}) == ["P2 a"]


def test_follow_chain_errors_name_the_poem(tmp_path):
    client, _ = fake_client(tmp_path, {"P1 a": "[[P1 gone|→]]"})
    with pytest.raises(ChainError, match="P1 a"):
        follow_chain(client, "P1 a", stop={"P1 a"})
    client, _ = fake_client(tmp_path / "loop", {"L a": "[[L b|→]]", "L b": "[[L a bis|→]]", "L a bis": "[[L b|→]]"})
    with pytest.raises(ChainError, match="loop"):
        follow_chain(client, "L a", stop=set())
```

- [ ] **Step 6: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_harvest.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 7: Write `pipeline/leggo_pipeline/harvest.py`**

```python
"""Fetch WikiLeopardi pages (cached) and follow each poem's chain of pages."""
from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path

import requests

API = "https://wikileopardi.altervista.org/wiki_leopardi/api.php"
USER_AGENT = "Mozilla/5.0 (compatible; LeggoLeopardi-pipeline/0.1; DH.ARC Bologna)"
INDEX_TITLE = "N35c Edizione critica"
NOTES_PREFIX = "N35c Note"
SKIP_INDEX = re.compile(r"FRONTESPIZIO|NOTIZIA|^N35c Note")
INDEX_ENTRY = re.compile(r"^\*\s*\[\[(N35c [^\]|]+)\|([^\]]+)\]\]", re.M)
NEXT = re.compile(r"\[\[([^\]|]+)\|\s*→[^\]]*\]\]")


class PageMissing(Exception):
    pass


class ChainError(Exception):
    pass


def _http_fetch(title: str) -> str | None:
    params = {"action": "query", "prop": "revisions", "rvprop": "content", "titles": title, "format": "json"}
    r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    page = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in page or "revisions" not in page:
        return None
    return page["revisions"][0]["*"]


class WikiClient:
    def __init__(self, cache_dir: Path, fetch: Callable[[str], str | None] | None = None, delay: float = 0.5):
        self.cache_dir = Path(cache_dir)
        self.fetch = fetch or _http_fetch
        self.delay = delay

    def _path(self, title: str) -> Path:
        return self.cache_dir / (hashlib.sha1(title.encode("utf-8")).hexdigest() + ".wiki")

    def page(self, title: str) -> str:
        path = self._path(title)
        if path.exists():
            return path.read_text(encoding="utf-8")
        text = self.fetch(title)
        if self.delay:
            time.sleep(self.delay)
        if text is None:
            raise PageMissing(title)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text


def parse_index(wikitext: str) -> list[tuple[str, str]]:
    return [
        (page.strip(), label.strip())
        for page, label in INDEX_ENTRY.findall(wikitext)
        if not SKIP_INDEX.search(page)
    ]


def next_page(wikitext: str) -> str | None:
    links = NEXT.findall(wikitext)
    return links[-1].strip() if links else None


def follow_chain(client: WikiClient, entry: str, stop: set[str], max_pages: int = 30) -> list[str]:
    pages = [entry]
    title = entry
    while True:
        try:
            nxt = next_page(client.page(title))
        except PageMissing as e:
            raise ChainError(f"poem starting at {entry!r}: page {e} does not exist") from e
        if nxt is None or nxt in stop or nxt.startswith(NOTES_PREFIX):
            return pages
        if nxt in pages:
            raise ChainError(f"poem starting at {entry!r}: loop at {nxt!r}")
        pages.append(nxt)
        if len(pages) > max_pages:
            raise ChainError(f"poem starting at {entry!r}: more than {max_pages} pages")
        title = nxt
```

- [ ] **Step 8: Run all tests and see them pass**

Run: `cd pipeline && uv run pytest -q`
Expected: all tests pass (`25 passed`).

- [ ] **Step 9: Check the live API once, which costs one request**

Run: `cd pipeline && uv run python -c "from leggo_pipeline.harvest import WikiClient, INDEX_TITLE, parse_index; from leggo_pipeline import paths; print(len(parse_index(WikiClient(paths.CACHE).page(INDEX_TITLE))))"`
Expected: `41`. If you get `403 Forbidden`, set `USER_AGENT = "curl/7.81.0"`, which was verified to work on 2026-09-30, then re-run.

- [ ] **Step 10: Commit**

```bash
git add pipeline/leggo_pipeline/tokens.py pipeline/leggo_pipeline/harvest.py pipeline/tests/test_tokens.py pipeline/tests/test_harvest.py
git commit -m "Add verse tokenizer and cached WikiLeopardi harvester

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Manifest `canti.json`

**Files:**
- Create: `pipeline/leggo_pipeline/manifest.py`
- Create (generated, then hand-edited): `canti.json`
- Test: `pipeline/tests/test_manifest.py`

**Interfaces:**
- Consumes: `WikiClient`, `INDEX_TITLE`, `parse_index`, `follow_chain` (Task 4).
- Produces:
  - `roman_to_int(r: str) -> int`
  - `slugify(title: str) -> str`
  - `build_manifest(entries: list[tuple[str, str]], chains: list[list[str]]) -> list[dict]`
  - `merge_existing(new: list[dict], old: list[dict]) -> list[dict]`
  - `load_manifest(path: Path) -> list[dict]`
  - A CLI, `python -m leggo_pipeline.manifest`.
  - Each entry has these keys: `n, roman, title, slug, base_witness, witnesses, title_variants, wiki_pages, pre_roles, status`. `status` is a dict `{leggo, traduco, collaziono, concordanza}` with values `none|provisional|verified`.

- [ ] **Step 1: Write the failing `pipeline/tests/test_manifest.py`**

```python
from leggo_pipeline.manifest import build_manifest, merge_existing, roman_to_int, slugify


def test_roman_and_slug():
    assert [roman_to_int(r) for r in ["I", "IV", "IX", "XII", "XXXIX", "XL", "XLI"]] == [1, 4, 9, 12, 39, 40, 41]
    assert slugify("L'infinito") == "l-infinito"
    assert slugify("La sera del dì di festa") == "la-sera-del-di-di-festa"
    assert slugify("") == ""


def test_build_manifest_entries():
    entries = [("N35c I. p. 7", "I. All'Italia"), ("N35c XXXVII. p. 161", "XXXVII.")]
    chains = [["N35c I. p. 7", "N35c I. p. 8"], ["N35c XXXVII. p. 161"]]
    m = build_manifest(entries, chains)
    assert m[0] == {
        "n": 1, "roman": "I", "title": "All'Italia", "slug": "all-italia",
        "base_witness": "N35c", "witnesses": ["N35c"], "title_variants": [],
        "wiki_pages": ["N35c I. p. 7", "N35c I. p. 8"], "pre_roles": None,
        "status": {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"},
    }
    assert m[1]["n"] == 37 and m[1]["title"] == "" and m[1]["slug"] == "frammento-xxxvii"


def test_merge_keeps_hand_edits_but_refreshes_pages():
    new = build_manifest([("E p. 1", "XII. L'infinito")], [["E p. 1"]])
    old = [dict(new[0], title="L'infinito (rivisto)", pre_roles=["head", "head"], wiki_pages=["old"])]
    merged = merge_existing(new, old)
    assert merged[0]["title"] == "L'infinito (rivisto)"
    assert merged[0]["pre_roles"] == ["head", "head"]
    assert merged[0]["wiki_pages"] == ["E p. 1"]
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_manifest.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/leggo_pipeline/manifest.py`**

```python
"""Build, merge and load canti.json, the list of the 41 Canti."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from . import paths
from .harvest import INDEX_TITLE, WikiClient, follow_chain, parse_index

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
HAND_KEYS = ("title", "title_variants", "pre_roles", "status", "base_witness", "witnesses")


def roman_to_int(r: str) -> int:
    total = 0
    for i, ch in enumerate(r):
        v = ROMAN[ch]
        total += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
    return total


def slugify(title: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def build_manifest(entries: list[tuple[str, str]], chains: list[list[str]]) -> list[dict]:
    manifest = []
    for (entry, label), chain in zip(entries, chains, strict=True):
        m = re.match(r"\s*([IVXL]+)\.\s*(.*)$", label)
        if not m:
            raise ValueError(f"index label without roman numeral: {label!r}")
        roman, title = m.group(1), m.group(2).strip()
        manifest.append(
            {
                "n": roman_to_int(roman),
                "roman": roman,
                "title": title,
                "slug": slugify(title) or f"frammento-{roman.lower()}",
                "base_witness": "N35c",
                "witnesses": ["N35c"],
                "title_variants": [],
                "wiki_pages": chain,
                "pre_roles": None,
                "status": {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"},
            }
        )
    return manifest


def merge_existing(new: list[dict], old: list[dict]) -> list[dict]:
    by_n = {e["n"]: e for e in old}
    merged = []
    for e in new:
        keep = by_n.get(e["n"], {})
        merged.append({**e, **{k: keep[k] for k in HAND_KEYS if k in keep}})
    return merged


def load_manifest(path: Path = paths.CANTI) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    client = WikiClient(paths.CACHE)
    entries = parse_index(client.page(INDEX_TITLE))
    stop = {page for page, _ in entries}
    chains = [follow_chain(client, page, stop) for page, _ in entries]
    manifest = build_manifest(entries, chains)
    if paths.CANTI.exists():
        manifest = merge_existing(manifest, load_manifest())
    ns = [e["n"] for e in manifest]
    if ns != list(range(1, len(ns) + 1)):
        raise SystemExit(f"poem numbers are not 1..{len(ns)}: {ns}")
    paths.CANTI.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {paths.CANTI} with {len(manifest)} poems, {sum(len(e['wiki_pages']) for e in manifest)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `cd pipeline && uv run pytest tests/test_manifest.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Generate `canti.json` from the live wiki**

This fetches about 230 pages, around 2–3 minutes at 0.5 s each. Pages are cached, so re-runs are free.

Run: `cd pipeline && uv run python -m leggo_pipeline.manifest`
Expected: `wrote …/canti.json with 41 poems, 2xx pages`.

- [ ] **Step 6: Check the page chains**

Run: `cd pipeline && uv run python -c "from leggo_pipeline.manifest import load_manifest; [print(e['n'], e['roman'], len(e['wiki_pages']), e['wiki_pages'][0][:50]) for e in load_manifest()]"`

Expected page counts, verified on 2026-09-30:

```
I 6, II 9, III 8, IV 5, V 3, VI 5, VII 4, VIII 5, IX 3, X 4, XI 3, XII 1, XIII 2, XIV 1, XV 4, XVI 5,
XVII 6, XVIII 3, XIX 7, XX 7, XXI 3, XXII 7, XXIII 6, XXIV 3, XXV 3, XXVI 7, XXVII 6, XXVIII 1, XXIX 5,
XXX 5, XXXI 3, XXXII 11, XXXIII 5, XXXIV 17, XXXV 1, XXXVI 1, XXXVII 2, XXXVIII 1, XXXIX 3, XL 2, XLI 2
```

If any count differs, open that poem's pages on the wiki and find out why before continuing. Do not edit `wiki_pages` by hand without noting the reason in the commit message.

- [ ] **Step 7: Commit**

```bash
git add pipeline/leggo_pipeline/manifest.py pipeline/tests/test_manifest.py canti.json
git commit -m "Generate canti.json from the WikiLeopardi N35c index

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: TEI base files (`build_base`)

**Files:**
- Create: `pipeline/leggo_pipeline/build_base.py`
- Test: `pipeline/tests/test_build_base.py`

**Interfaces:**
- Consumes: `parse_pages`, `ParsedPoem`, `Line` (Task 3); `tokenize` (Task 4); `WikiClient` (Task 4); `load_manifest` (Task 5); `paths`.
- Produces:
  - `TEI_NS = "http://www.tei-c.org/ns/1.0"`.
  - `build_poem_tei(entry: dict, parsed: ParsedPoem) -> bytes`. It writes UTF-8 TEI and raises `ValueError` if `pre_roles` doesn't fit.
  - `render_report(rows: list[tuple[dict, ParsedPoem]]) -> str`.
  - `build_all(manifest, client, tei_dir, loci_dir, report_path) -> None`.
  - A CLI, `python -m leggo_pipeline.build_base [--show-pre]`.
  - TEI shape:
    - `div[@type=canto][@n][@xml:id=c{n}]` contains `head` (with `lb` between the title lines), an optional `epigraph/l`, and `lg[@type=stanza]`.
    - Each `lg` holds `l[@n][@xml:id][@rend=indent{k}?]` and `label[@type=speaker]`.
    - Inside `l`: `w[@xml:id][@rend=italic?]`, `pc`, and `ref[@type=authorNote]`.
    - A missing verse is `l[@n]/gap[@reason=missing-in-source]`.
    - A line without a verse number is `l[@xml:id=c{n}.v{v}.u{j}]` with no `@n`.
    - The string value of each `l` equals the verse text exactly.

- [ ] **Step 1: Write the failing `pipeline/tests/test_build_base.py`**

```python
from pathlib import Path

import pytest
from lxml import etree

from leggo_pipeline.build_base import TEI_NS, build_poem_tei
from leggo_pipeline.wikitext import parse_pages

FIXTURES = Path(__file__).parent / "fixtures"
NS = {"tei": TEI_NS}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

INFINITO_ENTRY = {
    "n": 12, "roman": "XII", "title": "L'infinito", "slug": "l-infinito",
    "wiki_pages": ["N35c XII. ‖ L'INFINITO. p. 62"], "pre_roles": None,
}
SYN_ENTRY = {"n": 99, "roman": "X", "title": "Prova", "slug": "prova", "wiki_pages": ["P"], "pre_roles": ["head", "head", "speaker"]}
SYN_PAGE = """<poem>
X.
[[Titolo: PROVA.|PROVA.]]
ALCETA.
1 Prima verso,
2 &nbsp;&nbsp;secondo rientrato;
4&nbsp;&nbsp;&nbsp;&nbsp; quarto, nuova strofa.
MELISSO.
mezzo verso senza numero,
5 il lúgubri dì d’un ''walser'' ([[N35c Note p. 176|12]]).
</poem>"""


def infinito_tree():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    parsed = parse_pages([(INFINITO_ENTRY["wiki_pages"][0], text)])
    return etree.fromstring(build_poem_tei(INFINITO_ENTRY, parsed))


def syn_tree():
    return etree.fromstring(build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))


def test_infinito_verses_are_exact():
    from test_wikitext import INFINITO

    root = infinito_tree()
    ls = root.xpath("//tei:l[@n]", namespaces=NS)
    assert [l.get("n") for l in ls] == [str(i) for i in range(1, 16)]
    assert ["".join(l.itertext()) for l in ls] == INFINITO


def test_infinito_ids_head_and_header():
    root = infinito_tree()
    ws = root.xpath("//tei:l[@n='1']/tei:w", namespaces=NS)
    assert [w.get(XML_ID) for w in ws] == [f"c12.v1.w{i}" for i in range(1, 8)]
    assert ws[4].text == "quest’"
    head = root.xpath("//tei:head", namespaces=NS)[0]
    assert [head.text] + [lb.tail for lb in head] == ["XII.", "L'INFINITO."]
    assert root.xpath("string(//tei:revisionDesc/@status)", namespaces=NS) == "provisional"
    assert root.xpath("//tei:div/@xml:id", namespaces=NS) == ["c12"]


def test_build_is_deterministic():
    text = (FIXTURES / "n35c_infinito_p62.wiki").read_text(encoding="utf-8")
    parsed = parse_pages([("p", text)])
    assert build_poem_tei(INFINITO_ENTRY, parsed) == build_poem_tei(INFINITO_ENTRY, parsed)


def test_gap_indent_speakers_unnumbered_italic_ref():
    root = syn_tree()
    lgs = root.xpath("//tei:lg", namespaces=NS)
    assert len(lgs) == 2
    assert lgs[0][0].tag == f"{{{TEI_NS}}}label" and lgs[0][0].text == "ALCETA."
    assert root.xpath("//tei:l[@n='2']/@rend", namespaces=NS) == ["indent2"]
    assert root.xpath("//tei:l[@n='3']/tei:gap/@reason", namespaces=NS) == ["missing-in-source"]
    assert root.xpath("//tei:lg[2]/tei:label/text()", namespaces=NS) == ["MELISSO."]
    unnumbered = root.xpath("//tei:l[not(@n)]", namespaces=NS)
    assert [l.get(XML_ID) for l in unnumbered if l.getparent().tag.endswith("lg")] == ["c99.v4.u1"]
    v5 = root.xpath("//tei:l[@n='5']", namespaces=NS)[0]
    assert "".join(v5.itertext()) == "il lúgubri dì d’un walser (12)."
    assert v5.xpath("tei:w[@rend='italic']/text()", namespaces=NS) == ["walser"]
    assert v5.xpath("tei:ref[@type='authorNote']/text()", namespaces=NS) == ["12"]


def test_characters_survive_byte_for_byte():
    data = build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)]))
    for s in ["lúgubri", "dì", "d’un"]:
        assert s.encode("utf-8") in data
    nfd_page = SYN_PAGE.replace("dì", "dì")
    nfd = build_poem_tei(SYN_ENTRY, parse_pages([("P", nfd_page)]))
    assert "dì".encode("utf-8") in nfd and "dì".encode("utf-8") not in nfd


def test_pre_roles_must_fit():
    bad = dict(SYN_ENTRY, pre_roles=["head"])
    with pytest.raises(ValueError, match="pre_roles"):
        build_poem_tei(bad, parse_pages([("P", SYN_PAGE)]))


def test_epigraph_role():
    page = "<poem>\nXXVII.\nAMORE E MORTE.\nὋν οἱ θεοί φιλοῦσιν, ἀποθνήσκει νέος.\nmenandro.\n1 Fratelli, a un tempo stesso, Amore e Morte\n</poem>"
    entry = dict(SYN_ENTRY, n=27, pre_roles=["head", "head", "epigraph", "epigraph"])
    root = etree.fromstring(build_poem_tei(entry, parse_pages([("P", page)])))
    assert root.xpath("//tei:epigraph/tei:l/text()", namespaces=NS) == ["Ὃν οἱ θεοί φιλοῦσιν, ἀποθνήσκει νέος.", "menandro."]
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_build_base.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'leggo_pipeline.build_base'`.

- [ ] **Step 3: Write `pipeline/leggo_pipeline/build_base.py`**

```python
"""Build tei/base/c{n}.xml (N35c reading text) from cached WikiLeopardi pages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

from lxml import etree

from . import paths
from .harvest import WikiClient
from .manifest import load_manifest
from .tokens import tokenize
from .wikitext import Line, ParsedPoem, parse_pages

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
WIKI_URL = "https://wikileopardi.altervista.org/wiki_leopardi/index.php?title="
ROLES = {"head", "epigraph", "speaker"}
# Elements whose children are laid out one per line. Mixed-content elements (l, head, bibl)
# are never re-indented, so their string value stays exactly the source text.
STRUCTURAL = {
    "TEI", "teiHeader", "fileDesc", "titleStmt", "publicationStmt", "sourceDesc",
    "revisionDesc", "text", "body", "div", "lg", "epigraph",
}


def _el(parent, tag: str, text: str | None = None, **attrs: str):
    el = etree.SubElement(parent, f"{{{TEI_NS}}}{tag}")
    for k, v in attrs.items():
        el.set(k, v)
    if text:
        el.text = text
    return el


def _layout(root) -> None:
    for el in root.iter():
        name = etree.QName(el).localname
        if name in STRUCTURAL and len(el) and not (el.text and el.text.strip()):
            el.text = "\n"
        parent = el.getparent()
        if parent is not None and etree.QName(parent).localname in STRUCTURAL and not (el.tail and el.tail.strip()):
            el.tail = "\n"


def _fill_line(l, line: Line, id_prefix: str) -> None:
    toks = tokenize(line.text, line.italic, line.notes)
    l.text = (line.text[: toks[0].start] if toks else line.text) or None
    last, prev_end, w = None, 0, 0
    for t in toks:
        if last is not None:
            last.tail = line.text[prev_end : t.start] or None
        if t.kind == "w":
            w += 1
            el = _el(l, "w", t.text)
            el.set(XML_ID, f"{id_prefix}.w{w}")
        elif t.kind == "ref":
            el = _el(l, "ref", t.text, type="authorNote")
        else:
            el = _el(l, "pc", t.text)
        if t.italic:
            el.set("rend", "italic")
        last, prev_end = el, t.end
    if last is not None:
        last.tail = line.text[prev_end:] or None


def build_poem_tei(entry: dict, parsed: ParsedPoem) -> bytes:
    n = entry["n"]
    roles = entry.get("pre_roles") or ["head"] * len(parsed.pre)
    if len(roles) != len(parsed.pre) or not set(roles) <= ROLES:
        raise ValueError(
            f"c{n}: pre_roles {roles} does not fit the {len(parsed.pre)} lines before verse 1: {parsed.pre}"
        )

    tei = etree.Element(f"{{{TEI_NS}}}TEI", nsmap={None: TEI_NS})
    header = _el(tei, "teiHeader")
    fd = _el(header, "fileDesc")
    _el(_el(fd, "titleStmt"), "title", f"{entry['roman']}. {entry['title']}".strip())
    _el(_el(fd, "publicationStmt"), "p", "LeggoLeopardi. Testo base provvisorio, da verificare.")
    bibl = _el(
        _el(fd, "sourceDesc"),
        "bibl",
        "Canti, Napoli, Starita, 1835, esemplare corretto (N35c). Trascrizione: WikiLeopardi.",
    )
    for page in entry["wiki_pages"]:
        _el(bibl, "ptr", target=WIKI_URL + quote(page.replace(" ", "_")))
    rd = _el(header, "revisionDesc", status="provisional")
    _el(rd, "change", "Generato da pipeline/leggo_pipeline/build_base.py a partire da WikiLeopardi.")

    div = _el(_el(_el(tei, "text"), "body"), "div", type="canto", n=str(n))
    div.set(XML_ID, f"c{n}")
    heads = [t for t, r in zip(parsed.pre, roles) if r == "head"]
    if heads:
        head = _el(div, "head", heads[0])
        for t in heads[1:]:
            _el(head, "lb").tail = t
    epigraph = [t for t, r in zip(parsed.pre, roles) if r == "epigraph"]
    if epigraph:
        ep = _el(div, "epigraph")
        for t in epigraph:
            _el(ep, "l", t)
    speakers = [t for t, r in zip(parsed.pre, roles) if r == "speaker"]

    pending = sorted(parsed.missing)
    lg = None
    last_n = 0
    unnumbered = 0
    for line in parsed.lines:
        if line.kind == "verse":
            if lg is None or line.stanza_start:
                first = lg is None
                lg = _el(div, "lg", type="stanza")
                if first:
                    for s in speakers:
                        _el(lg, "label", s, type="speaker")
            while pending and pending[0] < line.n:
                g = pending.pop(0)
                gl = _el(lg, "l", n=str(g))
                gl.set(XML_ID, f"c{n}.v{g}")
                _el(gl, "gap", reason="missing-in-source")
            l = _el(lg, "l", n=str(line.n))
            l.set(XML_ID, f"c{n}.v{line.n}")
            if line.indent:
                l.set("rend", f"indent{line.indent}")
            _fill_line(l, line, f"c{n}.v{line.n}")
            last_n, unnumbered = line.n, 0
        else:
            if lg is None:
                lg = _el(div, "lg", type="stanza")
            if line.kind == "label":
                _el(lg, "label", line.text, type="speaker")
            else:
                unnumbered += 1
                pid = f"c{n}.v{last_n}.u{unnumbered}"
                l = _el(lg, "l")
                l.set(XML_ID, pid)
                _fill_line(l, line, pid)
    _layout(tei)
    return etree.tostring(tei, xml_declaration=True, encoding="UTF-8")


def render_report(rows: list[tuple[dict, ParsedPoem]]) -> str:
    out = [
        "# Base text report (WikiLeopardi → tei/base)",
        "",
        "Generated by `python -m leggo_pipeline.build_base`. Review every line under *Problems*.",
        "",
        "| n | canto | verses | stanzas | missing | speakers | unnumbered |",
        "|---|---|---|---|---|---|---|",
    ]
    problems: list[str] = []
    for entry, p in rows:
        verses = [l for l in p.lines if l.kind == "verse"]
        out.append(
            f"| {entry['n']} | {entry['roman']}. {entry['title']} | {len(verses)} | "
            f"{sum(l.stanza_start for l in verses)} | {', '.join(map(str, p.missing)) or '–'} | "
            f"{sum(l.kind == 'label' for l in p.lines)} | {sum(l.kind == 'unnumbered' for l in p.lines)} |"
        )
        problems += [f"- c{entry['n']}: {x}" for x in p.problems]
        if len(verses) > 30 and sum(l.stanza_start for l in verses) == 1:
            problems.append(f"- c{entry['n']}: one stanza only in {len(verses)} verses; check stanza breaks")
    out += ["", "## Problems", ""] + (problems or ["None."])
    return "\n".join(out) + "\n"


def _parse(client: WikiClient, entry: dict) -> ParsedPoem:
    return parse_pages([(t, client.page(t)) for t in entry["wiki_pages"]])


def build_all(manifest: list[dict], client: WikiClient, tei_dir: Path, loci_dir: Path, report_path: Path) -> None:
    tei_dir.mkdir(parents=True, exist_ok=True)
    loci_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in manifest:
        parsed = _parse(client, entry)
        (tei_dir / f"c{entry['n']}.xml").write_bytes(build_poem_tei(entry, parsed))
        loci = [
            {"verse": l.n, "target": s.target, "shown": l.text[s.start : s.end], "start": s.start, "end": s.end}
            for l in parsed.lines
            if l.kind == "verse"
            for s in l.loci
        ]
        (loci_dir / f"c{entry['n']}.json").write_text(
            json.dumps(loci, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        rows.append((entry, parsed))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show-pre", action="store_true", help="print the lines before verse 1 of every poem and exit")
    args = ap.parse_args(argv)
    manifest = load_manifest(paths.CANTI)
    client = WikiClient(paths.CACHE)
    if args.show_pre:
        for e in manifest:
            print(f"c{e['n']} {e['roman']}: {_parse(client, e).pre}  pre_roles={e.get('pre_roles')}")
        return 0
    build_all(manifest, client, paths.TEI_BASE, paths.LOCI, paths.REPORTS / "base_report.md")
    print(f"wrote {len(manifest)} files to {paths.TEI_BASE}; report: {paths.REPORTS / 'base_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `cd pipeline && uv run pytest tests/test_build_base.py -q`
Expected: `7 passed`. `test_infinito_verses_are_exact` imports `INFINITO` from `test_wikitext`, which works because pytest puts `tests/` on `sys.path` (rootdir-relative, no `__init__.py`).

- [ ] **Step 5: Commit**

```bash
git add pipeline/leggo_pipeline/build_base.py pipeline/tests/test_build_base.py
git commit -m "Write provisional N35c TEI with stable verse and word ids

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Validation and site data

**Files:**
- Create: `pipeline/leggo_pipeline/validate.py`, `pipeline/leggo_pipeline/build_site_data.py`
- Test: `pipeline/tests/test_validate.py`, `pipeline/tests/test_build_site_data.py`

**Interfaces:**
- Consumes: `build_poem_tei`, `TEI_NS` (Task 6); `load_manifest` (Task 5); `paths`.
- Produces:
  - `validate(tei_dir: Path, manifest: list[dict], schema_path: Path | None) -> list[str]`, which returns error messages (empty means valid). CLI: `python -m leggo_pipeline.validate` exits with 1 on errors.
  - `poem_json(entry: dict, tei_path: Path) -> dict`.
  - `build_site(manifest, tei_dir: Path, out_dir: Path) -> None`, which writes `c{n}.json` and `index.json`. CLI: `python -m leggo_pipeline.build_site_data`.
- JSON contract used by the app (Tasks 9–10):
  - `index.json`: `[{n, roman, title, slug, incipit, status}]`.
  - `c{n}.json`: `{n, roman, title, slug, incipit, status, source: {label, status, pages: [url]}, head: [str], epigraph: [str], stanzas: [[item]]}`.
  - Each item is `{"type": "l", "n": int|null, "id": str, "indent": int, "missing": bool, "unnumbered": bool, "text": str, "html": str}` or `{"type": "label", "text": str}`.
  - `html` is the text with only `&`, `<`, `>` escaped (quotes and apostrophes stay as they are), with `<em>` for italic words and `<sup class="noteref">` for note calls.

- [ ] **Step 1: Write the failing `pipeline/tests/test_validate.py`**

```python
from lxml import etree

from leggo_pipeline import paths
from leggo_pipeline.validate import validate
from test_build_base import INFINITO_ENTRY, SYN_ENTRY, SYN_PAGE, infinito_tree
from leggo_pipeline.build_base import build_poem_tei
from leggo_pipeline.wikitext import parse_pages


def write(tmp_path, n, data: bytes):
    (tmp_path / f"c{n}.xml").write_bytes(data)


def test_generated_tei_is_valid_against_tei_all(tmp_path):
    write(tmp_path, 12, etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    write(tmp_path, 99, build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))
    assert validate(tmp_path, [{"n": 12}, {"n": 99}], paths.SCHEMA) == []


def test_missing_file_and_bad_numbering_and_duplicate_ids(tmp_path):
    data = etree.tostring(infinito_tree(), encoding="UTF-8").decode()
    write(tmp_path, 12, data.replace('n="7" xml:id="c12.v7"', 'n="70" xml:id="c12.v7"').encode())
    write(tmp_path, 13, data.replace("c12.v2.w1", "c12.v1.w1").replace('xml:id="c12"', 'xml:id="c13"').encode())
    errors = validate(tmp_path, [{"n": 12}, {"n": 13}, {"n": 14}], None)
    assert any("c12.xml" in e and "verse numbers" in e for e in errors)
    assert any("c13.xml" in e and "duplicate xml:id c12.v1.w1" in e for e in errors)
    assert any("c13.xml" in e and "id c12." in e for e in errors)
    assert "c14.xml: missing" in errors
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_validate.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Write `pipeline/leggo_pipeline/validate.py`**

```python
"""Check tei/base: schema validity, unique well-formed ids, verse numbering, one file per poem."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from lxml import etree

from . import paths
from .manifest import load_manifest

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def validate(tei_dir: Path, manifest: list[dict], schema_path: Path | None) -> list[str]:
    errors: list[str] = []
    rng = etree.RelaxNG(etree.parse(str(schema_path))) if schema_path else None
    for entry in manifest:
        n = entry["n"]
        path = Path(tei_dir) / f"c{n}.xml"
        if not path.exists():
            errors.append(f"{path.name}: missing")
            continue
        try:
            doc = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            errors.append(f"{path.name}: not well-formed: {e}")
            continue
        if rng is not None and not rng.validate(doc):
            errors.append(f"{path.name}: schema: {rng.error_log.last_error}")
        ids = doc.xpath("//@xml:id")
        errors += [f"{path.name}: duplicate xml:id {i}" for i, c in Counter(ids).items() if c > 1]
        pattern = re.compile(rf"^c{n}(\.v\d+(\.u\d+)?(\.w\d+)?)?$")
        errors += [f"{path.name}: id {i} does not match c{n}.v…" for i in ids if not pattern.match(i)]
        numbers = [int(x) for x in doc.xpath("//tei:lg/tei:l/@n", namespaces=NS)]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{path.name}: verse numbers are not 1..{len(numbers)}")
    return errors


def main() -> int:
    errors = validate(paths.TEI_BASE, load_manifest(paths.CANTI), paths.SCHEMA)
    for e in errors:
        print(e)
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run it and see it pass**

Run: `cd pipeline && uv run pytest tests/test_validate.py -q`
Expected: `2 passed`. The schema test takes a few seconds to compile `tei_all.rng`. If `test_generated_tei_is_valid_against_tei_all` fails, fix `build_base.py` so the TEI is valid. Never loosen the test or the schema.

- [ ] **Step 5: Write the failing `pipeline/tests/test_build_site_data.py`**

```python
import json

from lxml import etree

from leggo_pipeline.build_base import build_poem_tei
from leggo_pipeline.build_site_data import build_site, poem_json
from leggo_pipeline.wikitext import parse_pages
from test_build_base import INFINITO_ENTRY, SYN_ENTRY, SYN_PAGE, infinito_tree
from test_wikitext import INFINITO

STATUS = {"leggo": "provisional", "traduco": "none", "collaziono": "none", "concordanza": "none"}


def test_infinito_json(tmp_path):
    (tmp_path / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    data = poem_json(dict(INFINITO_ENTRY, status=STATUS), tmp_path / "c12.xml")
    assert data["head"] == ["XII.", "L'INFINITO."]
    assert data["incipit"] == INFINITO[0]
    assert data["source"]["status"] == "provisional" and data["source"]["label"] == "WikiLeopardi"
    assert len(data["source"]["pages"]) == 1 and data["source"]["pages"][0].startswith("https://wikileopardi")
    [stanza] = data["stanzas"]
    assert [i["text"] for i in stanza] == INFINITO
    assert stanza[0] == {
        "type": "l", "n": 1, "id": "c12.v1", "indent": 0, "missing": False, "unnumbered": False,
        "text": INFINITO[0], "html": INFINITO[0],
    }


def test_special_items_and_html(tmp_path):
    (tmp_path / "c99.xml").write_bytes(build_poem_tei(SYN_ENTRY, parse_pages([("P", SYN_PAGE)])))
    data = poem_json(dict(SYN_ENTRY, status=STATUS), tmp_path / "c99.xml")
    items = [i for st in data["stanzas"] for i in st]
    assert items[0] == {"type": "label", "text": "ALCETA."}
    missing = next(i for i in items if i.get("n") == 3)
    assert missing["missing"] is True and missing["html"] == ""
    assert next(i for i in items if i.get("n") == 2)["indent"] == 2
    unnumbered = next(i for i in items if i.get("unnumbered"))
    assert unnumbered["n"] is None and unnumbered["id"] == "c99.v4.u1"
    v5 = next(i for i in items if i.get("n") == 5)
    assert v5["html"] == 'il lúgubri dì d’un <em>walser</em> (<sup class="noteref">12</sup>).'


def test_build_site_writes_index(tmp_path):
    tei, out = tmp_path / "tei", tmp_path / "out"
    tei.mkdir()
    (tei / "c12.xml").write_bytes(etree.tostring(infinito_tree(), xml_declaration=True, encoding="UTF-8"))
    build_site([dict(INFINITO_ENTRY, status=STATUS)], tei, out)
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert index == [{"n": 12, "roman": "XII", "title": "L'infinito", "slug": "l-infinito", "incipit": INFINITO[0], "status": STATUS}]
    assert (out / "c12.json").is_file()
```

- [ ] **Step 6: Run it and see it fail**

Run: `cd pipeline && uv run pytest tests/test_build_site_data.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 7: Write `pipeline/leggo_pipeline/build_site_data.py`**

```python
"""Turn tei/base into the static JSON the Express app serves (public/data)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from lxml import etree

from . import paths
from .manifest import load_manifest

TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
INDEX_KEYS = ("n", "roman", "title", "slug", "incipit", "status")


def _line_html(l) -> str:
    out = [html.escape(l.text or "", quote=False)]
    for ch in l:
        text = html.escape(ch.text or "", quote=False)
        if ch.tag == f"{TEI}ref":
            text = f'<sup class="noteref">{text}</sup>'
        elif ch.get("rend") == "italic":
            text = f"<em>{text}</em>"
        out.append(text)
        out.append(html.escape(ch.tail or "", quote=False))
    return "".join(out)


def _item(el) -> dict:
    if el.tag == f"{TEI}label":
        return {"type": "label", "text": el.text or ""}
    missing = el.find(f"{TEI}gap") is not None
    rend = el.get("rend") or ""
    return {
        "type": "l",
        "n": int(el.get("n")) if el.get("n") else None,
        "id": el.get(XML_ID),
        "indent": int(rend[len("indent"):]) if rend.startswith("indent") else 0,
        "missing": missing,
        "unnumbered": el.get("n") is None,
        "text": "" if missing else "".join(el.itertext()),
        "html": "" if missing else _line_html(el),
    }


def poem_json(entry: dict, tei_path: Path) -> dict:
    root = etree.parse(str(tei_path)).getroot()
    div = root.find(f".//{TEI}div")
    head_el = div.find(f"{TEI}head")
    head = [] if head_el is None else [head_el.text or ""] + [lb.tail or "" for lb in head_el]
    epigraph = [l.text or "" for l in div.findall(f"{TEI}epigraph/{TEI}l")]
    stanzas = [[_item(el) for el in lg] for lg in div.findall(f"{TEI}lg")]
    first = next((i for st in stanzas for i in st if i["type"] == "l" and not i["missing"]), None)
    return {
        "n": entry["n"],
        "roman": entry["roman"],
        "title": entry["title"],
        "slug": entry["slug"],
        "incipit": first["text"] if first else "",
        "status": entry["status"],
        "source": {
            "label": "WikiLeopardi",
            "status": root.xpath("string(//tei:revisionDesc/@status)", namespaces=NS),
            "pages": root.xpath("//tei:sourceDesc//tei:ptr/@target", namespaces=NS),
        },
        "head": head,
        "epigraph": epigraph,
        "stanzas": stanzas,
    }


def build_site(manifest: list[dict], tei_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for entry in manifest:
        data = poem_json(entry, Path(tei_dir) / f"c{entry['n']}.xml")
        (out_dir / f"c{entry['n']}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        index.append({k: data[k] for k in INDEX_KEYS})
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    manifest = load_manifest(paths.CANTI)
    build_site(manifest, paths.TEI_BASE, paths.DATA)
    print(f"wrote {len(manifest)} poems to {paths.DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 8: Run all pipeline tests and see them pass**

Run: `cd pipeline && uv run pytest -q`
Expected: all pass (`40 passed`).

- [ ] **Step 9: Commit**

```bash
git add pipeline/leggo_pipeline/validate.py pipeline/leggo_pipeline/build_site_data.py pipeline/tests/test_validate.py pipeline/tests/test_build_site_data.py
git commit -m "Validate base TEI and build the site JSON

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Build the real data for all 41 Canti (checkpoint with the user)

**Files:**
- Modify: `canti.json` (`pre_roles` only)
- Create (generated): `tei/base/c1.xml` … `c41.xml`, `pipeline/work/loci/c*.json`, `reports/base_report.md`, `public/data/index.json`, `public/data/c*.json`

**Interfaces:**
- Consumes: the CLIs from Tasks 5–7.
- Produces: the committed data that Tasks 9–12 rely on: `public/data/index.json` with 41 entries.

- [ ] **Step 1: Show the lines before verse 1 of every poem**

Run: `cd pipeline && uv run python -m leggo_pipeline.build_base --show-pre`

- [ ] **Step 2: Set `pre_roles` in `canti.json`**

The expected roles, established on 2026-09-30, are listed below. Confirm each against the Step 1 output: the lengths must match exactly. Leave every other poem at `null`, which means all its lines are title lines.

| n | lines before verse 1 (2026-09-30) | `pre_roles` |
|---|---|---|
| 27 | `XXVII.`, `AMORE E MORTE.`, Greek line, `Muor giovane colui ch’al cielo è caro.`, `menandro.` | `["head","head","epigraph","epigraph","epigraph"]` |
| 32 | `XXXII.`, `PALINODIA`, `AL MARCHESE GINO CAPPONI.`, `Il sempre sospirar nulla rileva.`, `petrarca.` | `["head","head","head","epigraph","epigraph"]` |
| 34 | `XXXIV.`, `La ginestra`, `o`, `il fiore del deserto.`, Greek line 1, Greek line 2, `Giovanni, III, 19` | `["head","head","head","head","epigraph","epigraph","epigraph"]` |
| 37 | `XXXVII.`, `ALCETA.` | `["head","speaker"]` |

If the output for any other poem shows something that is not a title line, stop and ask the user before assigning it a role.

- [ ] **Step 3: Build the TEI, validate it, build the JSON**

```bash
cd pipeline
uv run python -m leggo_pipeline.build_base
uv run python -m leggo_pipeline.validate
uv run python -m leggo_pipeline.build_site_data
```

Expected:
- `wrote 41 files …`
- `0 error(s)` (exit code 0)
- `wrote 41 poems …`

- [ ] **Step 4: Check the report against the known facts**

Run: `cat reports/base_report.md`

Expected:
- XII has 15 verses.
- XVII (*Consalvo*) shows `130` as missing.
- XXXIV has 317 verses and **no** missing verses: the `137 … 138 …` line is split.
- XXXVII has 2 speakers after verse 1 and 1 unnumbered line.
- XX (*Il risorgimento*) has 40 stanzas.
- X (*Il primo amore*) has 1 stanza, with indented verses.
- The Problems list contains the *Consalvo* gap, the XXXVII half-verse, and the "one stanza only" warnings, e.g. for XV *Il sogno*.

- [ ] **Step 5: Spot-check the text against the fixture**

Run: `cd pipeline && uv run python -c "import json; d=json.load(open('../public/data/c12.json')); print([i['text'] for i in d['stanzas'][0]][:3])"`
Expected: `['Sempre caro mi fu quest’ermo colle,', 'E questa siepe, che da tanta parte', "Dell'ultimo orizzonte il guardo esclude."]`

- [ ] **Step 6: CHECKPOINT: show the user `reports/base_report.md`**

Send the user the Problems section and ask how to proceed. Do not change any verse text by hand.

- [ ] **Step 7: Commit**

```bash
git add canti.json tei/base pipeline/work/loci reports/base_report.md public/data
git commit -m "Build provisional N35c base text for all 41 Canti

The text comes from WikiLeopardi; the gaps and unnumbered lines found are listed in reports/base_report.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Express app skeleton: home, poem list, i18n, 404

**Files:**
- Create: `package.json` (through npm), `app/app.js`, `app/server.js`, `app/data.js`
- Create: `app/locales/it.json`, `app/locales/en.json`
- Create: `app/views/partials/head.ejs`, `app/views/partials/nav.ejs`, `app/views/partials/footer.ejs`, `app/views/home.ejs`, `app/views/404.ejs`
- Create: `public/css/site.css`
- Test: `app/tests/app.test.js`

**Interfaces:**
- Consumes: `public/data/index.json` and `public/data/c{n}.json`, with the contract from Task 7.
- Produces:
  - `app/app.js` exports the Express app, which does not listen.
  - `app/data.js` exports `index(): Array` and `poem(param: string): object | null`. `poem` returns `null` for anything that is not a known poem number.
  - `res.locals`: `canti`, `lang`, `path`, `__`.

- [ ] **Step 1: Initialise npm and install dependencies**

```bash
npm init -y
npm install express@4 ejs@3 i18n@0.15 cookie-parser@1
npm install -D supertest@7
```

Then edit `package.json` so these fields read:

```json
  "name": "leggoleopardi",
  "private": true,
  "description": "LeggoLeopardi: digital edition of Leopardi's Canti",
  "main": "app/app.js",
  "engines": { "node": ">=22" },
  "scripts": {
    "start": "node app/server.js",
    "dev": "node --watch app/server.js",
    "test": "node --test app/tests/*.test.js"
  },
```

- [ ] **Step 2: Write the failing `app/tests/app.test.js`**

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

// The app must not depend on the working directory (Vercel runs it from elsewhere).
process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));

test('home lists every canto from index.json', async () => {
  assert.equal(index.length, 41);
  const res = await request(app).get('/');
  assert.equal(res.status, 200);
  assert.equal((res.text.match(/<li class="canto">/g) || []).length, index.length);
  assert.match(res.text, /<html lang="it">/);
});

test('language switch sets a cookie and redirects only to local paths', async () => {
  let res = await request(app).get('/lang/en?next=/leggo/12');
  assert.equal(res.status, 302);
  assert.equal(res.headers.location, '/leggo/12');
  assert.match(res.headers['set-cookie'].join(';'), /lang=en/);
  res = await request(app).get('/lang/en?next=//evil.example');
  assert.equal(res.headers.location, '/');
  res = await request(app).get('/').set('Cookie', 'lang=en');
  assert.match(res.text, /<html lang="en">/);
});

test('unknown pages are 404 with the site layout', async () => {
  const res = await request(app).get('/nope');
  assert.equal(res.status, 404);
  assert.match(res.text, /Leggo <b>Leopardi<\/b>/);
});
```

- [ ] **Step 3: Run it and see it fail**

Run: `npm test`
Expected: FAIL, `Cannot find module '…/app/app.js'`.

- [ ] **Step 4: Write `app/data.js`**

```js
const fs = require('node:fs');
const path = require('node:path');

const DATA_DIR = path.join(__dirname, '..', 'public', 'data');
let cachedIndex = null;
const poems = new Map();

function readJson(file) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8'));
}

/** The 41 Canti: [{ n, roman, title, slug, incipit, status }]. */
function index() {
  if (!cachedIndex) cachedIndex = readJson('index.json');
  return cachedIndex;
}

/** One poem's data, or null when `param` is not the number of a known poem. */
function poem(param) {
  if (!/^[1-9]\d?$/.test(String(param))) return null;
  const n = Number(param);
  if (!index().some((p) => p.n === n)) return null;
  if (!poems.has(n)) poems.set(n, readJson(`c${n}.json`));
  return poems.get(n);
}

module.exports = { index, poem };
```

- [ ] **Step 5: Write `app/app.js` and `app/server.js`**

`app/app.js`:

```js
const path = require('node:path');
const express = require('express');
const cookieParser = require('cookie-parser');
const i18n = require('i18n');
const data = require('./data');

i18n.configure({
  locales: ['it', 'en'],
  defaultLocale: 'it',
  directory: path.join(__dirname, 'locales'),
  cookie: 'lang',
  updateFiles: false,
  objectNotation: true,
});

const app = express();
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(cookieParser());
app.use(i18n.init);
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use((req, res, next) => {
  res.locals.canti = data.index();
  res.locals.lang = req.getLocale();
  res.locals.path = req.path;
  next();
});

app.get('/', (req, res) => res.render('home'));

app.get('/lang/:code', (req, res) => {
  const code = ['it', 'en'].includes(req.params.code) ? req.params.code : 'it';
  const next = typeof req.query.next === 'string' && /^\/(?!\/)/.test(req.query.next) ? req.query.next : '/';
  res.cookie('lang', code, { maxAge: 365 * 24 * 3600 * 1000, sameSite: 'lax' });
  res.redirect(next);
});

app.use((req, res) => res.status(404).render('404'));

module.exports = app;
```

`app/server.js`:

```js
const app = require('./app');

const port = Number(process.env.PORT) || 8000;
app.listen(port, () => console.log(`LeggoLeopardi on http://localhost:${port}`));
```

- [ ] **Step 6: Write the locales**

`app/locales/it.json`:

```json
{
  "nav": { "label": "Moduli", "soon": "In preparazione" },
  "home": {
    "eyebrow": "Edizione digitale dei Canti · Università di Bologna",
    "lede": "I Canti nel testo dell’esemplare corretto dell’edizione Starita (N35c), con i commenti storici, le traduzioni verso per verso e la collazione delle stampe.",
    "readInfinito": "Leggi L’infinito",
    "index": "Indice dei Canti",
    "canti": "I Canti",
    "vignetteAlt": "Pagina 62 dei Canti, Napoli, Starita 1835: XII. L’infinito",
    "vignetteCaption": "<i>Canti</i>, Napoli, Starita 1835, p. 62: XII. L’infinito. Esemplare corretto (N35c). Immagine: WikiLeopardi."
  },
  "status": { "none": "in preparazione", "provisional": "testo provvisorio", "verified": "verificato" },
  "leggo": {
    "choose": "Scegli un canto",
    "go": "Vai",
    "source": {
      "provisional": "Testo provvisorio (trascrizione WikiLeopardi, da verificare)",
      "verified": "Testo verificato"
    },
    "missingVerse": "[verso mancante nella fonte]",
    "unnumbered": "riga senza numero nella fonte"
  },
  "notFound": { "title": "Pagina non trovata", "body": "La pagina richiesta non esiste.", "home": "Torna all’inizio" },
  "footer": "Leggo Leopardi · DH.ARC, Università di Bologna"
}
```

`app/locales/en.json`:

```json
{
  "nav": { "label": "Modules", "soon": "Coming soon" },
  "home": {
    "eyebrow": "Digital edition of the Canti · University of Bologna",
    "lede": "The Canti in the text of the corrected copy of the Starita edition (N35c), with historical commentaries, verse-by-verse translations and the collation of the printed editions.",
    "readInfinito": "Read L’infinito",
    "index": "Index of the Canti",
    "canti": "The Canti",
    "vignetteAlt": "Page 62 of the Canti, Naples, Starita 1835: XII. L’infinito",
    "vignetteCaption": "<i>Canti</i>, Naples, Starita 1835, p. 62: XII. L’infinito. Corrected copy (N35c). Image: WikiLeopardi."
  },
  "status": { "none": "coming soon", "provisional": "provisional text", "verified": "verified" },
  "leggo": {
    "choose": "Choose a poem",
    "go": "Go",
    "source": {
      "provisional": "Provisional text (WikiLeopardi transcription, to be verified)",
      "verified": "Verified text"
    },
    "missingVerse": "[verse missing in the source]",
    "unnumbered": "line without a number in the source"
  },
  "notFound": { "title": "Page not found", "body": "The page you asked for does not exist.", "home": "Back to the start" },
  "footer": "Leggo Leopardi · DH.ARC, University of Bologna"
}
```

- [ ] **Step 7: Write the views**

`app/views/partials/head.ejs`:

```ejs
<!doctype html>
<html lang="<%= lang %>">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><%= typeof title !== 'undefined' && title ? title + ' · ' : '' %>Leggo Leopardi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Cormorant+SC:wght@500;600&display=swap">
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
```

`app/views/partials/nav.ejs`:

```ejs
<header class="nav">
  <div class="wrap nav-inner">
    <a class="brand" href="/">Leggo <b>Leopardi</b></a>
    <nav class="links" aria-label="<%= __('nav.label') %>">
      <a href="/leggo" class="<%= path.startsWith('/leggo') ? 'on' : '' %>">Leggo</a>
      <span class="soon" title="<%= __('nav.soon') %>">Traduco</span>
      <span class="soon" title="<%= __('nav.soon') %>">Collaziono</span>
      <span class="soon" title="<%= __('nav.soon') %>">Concordanza</span>
    </nav>
    <div class="lang">
      <a href="/lang/it?next=<%= encodeURIComponent(path) %>" class="<%= lang === 'it' ? 'on' : '' %>">IT</a>
      <a href="/lang/en?next=<%= encodeURIComponent(path) %>" class="<%= lang === 'en' ? 'on' : '' %>">EN</a>
    </div>
  </div>
</header>
```

`app/views/partials/footer.ejs`:

```ejs
<footer class="foot"><div class="wrap"><%= __('footer') %></div></footer>
</body>
</html>
```

`app/views/home.ejs`:

```ejs
<%- include('partials/head') %>
<%- include('partials/nav') %>
<main>
  <div class="wrap hero">
    <div>
      <p class="eyebrow"><%= __('home.eyebrow') %></p>
      <h1>Leggo <span>Leopardi</span></h1>
      <p class="lede"><%= __('home.lede') %></p>
      <% const inf = canti.find((p) => p.slug === 'l-infinito'); %>
      <div class="cta">
        <% if (inf) { %><a class="btn primary" href="/leggo/<%= inf.n %>"><%= __('home.readInfinito') %></a><% } %>
        <a class="btn ghost" href="#canti"><%= __('home.index') %></a>
      </div>
    </div>
    <figure class="vignette">
      <img src="/img/vignette-n35c-infinito.jpg" width="760" height="981" alt="<%= __('home.vignetteAlt') %>">
      <figcaption><%- __('home.vignetteCaption') %></figcaption>
    </figure>
  </div>
  <section id="canti" class="band-soft">
    <div class="wrap">
      <h2><%= __('home.canti') %></h2>
      <ol class="canti">
        <% canti.forEach((p) => { %><li class="canto"><span class="num"><%= p.roman %></span><a class="t" href="/leggo/<%= p.n %>"><%= p.title || p.incipit %></a><span class="st st-<%= p.status.leggo %>"><%= __('status.' + p.status.leggo) %></span></li>
        <% }) %>
      </ol>
    </div>
  </section>
</main>
<%- include('partials/footer') %>
```

`app/views/404.ejs`:

```ejs
<%- include('partials/head', { title: __('notFound.title') }) %>
<%- include('partials/nav') %>
<main class="wrap notfound">
  <h1><%= __('notFound.title') %></h1>
  <p><%= __('notFound.body') %></p>
  <p><a class="btn primary" href="/"><%= __('notFound.home') %></a></p>
</main>
<%- include('partials/footer') %>
```

- [ ] **Step 8: Write `public/css/site.css`**

This is the Ocean v1 palette. All colours are tokens in `:root`, so the warmer variant only replaces the first block.

```css
/* Palette "Ocean v1" (spec §8). A warmer variant will replace this block only. */
:root {
  --main: #2F6391;
  --dark: #0E3A62;
  --tint: #A9C8DB;
  --panel: #E6EFF6;
  --accent: #B8743A;
  --paper: #F7F4EA;
  --ink: #1B2733;
  --muted: #56697A;
  --line: #CCDCE8;
  --band: var(--main);
  --on-band: #F7F4EA;
  --display: "Cormorant Garamond", "EB Garamond", Garamond, Georgia, serif;
  --label: "Cormorant SC", "Cormorant Garamond", Garamond, Georgia, serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --main: #7FB0D6; --dark: #CFE2F0; --tint: #35597A; --panel: #152C42; --accent: #D99A5E;
    --paper: #0C1B2A; --ink: #E3ECF3; --muted: #9FB4C6; --line: #24425E; --band: #163F66; --on-band: #EEF3F7;
    color-scheme: dark;
  }
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--display); font-size: 1.2rem; line-height: 1.5; }
a { color: inherit; }
.wrap { max-width: 1120px; margin: 0 auto; padding-inline: clamp(16px, 4vw, 40px); }
.eyebrow { font-family: var(--label); letter-spacing: .08em; font-size: .95rem; color: var(--muted); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* navbar */
.nav { background: var(--band); color: var(--on-band); position: sticky; top: 0; z-index: 5; }
.nav-inner { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; padding-block: 12px; }
.brand { font-style: italic; font-size: 1.5rem; font-weight: 500; text-decoration: none; margin-right: auto; }
.brand b { font-style: normal; font-weight: 600; }
.links { display: flex; gap: 20px; flex-wrap: wrap; font-family: var(--label); font-size: 1.1rem; letter-spacing: .04em; }
.links a { text-decoration: none; border-bottom: 1px solid transparent; }
.links a.on, .links a:hover { border-color: var(--on-band); }
.links .soon { opacity: .55; cursor: default; }
.lang { display: flex; gap: 6px; font-family: var(--label); }
.lang a { text-decoration: none; padding: 1px 8px; border: 1px solid var(--on-band); border-radius: 3px; opacity: .8; }
.lang a.on { background: var(--on-band); color: var(--band); opacity: 1; }

/* home */
.hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr); gap: clamp(24px, 5vw, 64px); align-items: center; padding-block: clamp(32px, 6vw, 72px); }
.hero h1 { font-size: clamp(3.2rem, 8vw, 6rem); line-height: .95; font-weight: 500; font-style: italic; color: var(--dark); margin: .2em 0 .25em; }
.hero h1 span { display: block; font-style: normal; font-weight: 600; }
.lede { font-size: 1.35rem; max-width: 34em; }
.cta { display: flex; gap: 14px; flex-wrap: wrap; }
.btn { font-family: var(--label); font-size: 1.15rem; letter-spacing: .04em; text-decoration: none; padding: 8px 18px; border-radius: 3px; border: 1px solid var(--main); }
.btn.primary { background: var(--main); color: var(--paper); }
.btn.ghost { color: var(--main); }
.vignette { margin: 0; justify-self: center; max-width: 420px; width: 100%; }
.vignette img { display: block; width: 100%; height: auto; border: 1px solid var(--line); }
.vignette figcaption { font-size: 1rem; color: var(--muted); margin-top: 10px; }
.band-soft { background: var(--panel); padding-block: clamp(28px, 5vw, 56px); }
h2 { font-weight: 500; color: var(--dark); font-size: clamp(1.9rem, 4vw, 2.6rem); margin: 0 0 .6em; }
.canti { list-style: none; margin: 0; padding: 0; columns: 3 18rem; column-gap: 36px; }
.canto { break-inside: avoid; display: grid; grid-template-columns: 3.4em minmax(0, 1fr) auto; gap: 8px; align-items: baseline; padding: 5px 0; border-bottom: 1px solid var(--line); font-size: 1.1rem; }
.canto .num { font-family: var(--label); color: var(--muted); text-align: right; }
.canto .t { text-decoration: none; }
.canto .t:hover { color: var(--main); text-decoration: underline; }
.st { font-family: var(--label); font-size: .8rem; padding: 0 7px; border-radius: 9px; white-space: nowrap; border: 1px solid var(--tint); color: var(--muted); }
.st-verified { background: var(--main); color: var(--paper); border-color: var(--main); }

/* leggo */
.leggo { padding-block: clamp(20px, 4vw, 40px); }
.poem-select { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 24px; }
.poem-select select { font: inherit; font-size: 1.05rem; max-width: 100%; padding: 4px 8px; border: 1px solid var(--tint); border-radius: 3px; background: var(--paper); color: var(--ink); }
.poem-select button { font-family: var(--label); font-size: 1rem; padding: 4px 12px; border: 1px solid var(--main); border-radius: 3px; background: var(--main); color: var(--paper); cursor: pointer; }
.poem { max-width: 40rem; }
.badge { display: inline-block; font-family: var(--label); font-size: .9rem; color: var(--muted); border: 1px dashed var(--tint); padding: 2px 10px; border-radius: 3px; }
.poem-head { font-weight: 500; color: var(--dark); font-size: clamp(1.6rem, 3.5vw, 2.2rem); line-height: 1.2; margin: .6em 0 .8em; }
.poem-head span { display: block; }
.epigraph { margin: 0 0 1.5em 2.5em; font-style: italic; color: var(--muted); }
.epigraph p { margin: 0; }
.stanza { margin-bottom: 1.1em; }
.verse { display: grid; grid-template-columns: 2.6em minmax(0, 1fr); margin: 0; }
.verse .vn { font-family: var(--label); font-size: .85rem; color: var(--muted); text-align: right; padding-right: .9em; padding-top: .25em; }
.verse.indent1 .vt { padding-left: 1.2em; }
.verse.indent2 .vt { padding-left: 2.4em; }
.verse.missing .vt { color: var(--muted); font-style: italic; }
.verse.unnumbered .vt { color: var(--muted); }
.speaker { font-family: var(--label); letter-spacing: .05em; color: var(--accent); margin: .6em 0 .1em 2.6em; }
.noteref { font-size: .7em; color: var(--accent); }

/* 404 and footer */
.notfound { padding-block: 60px; }
.foot { background: var(--dark); color: var(--paper); padding-block: 22px; font-size: 1rem; margin-top: 40px; }
@media (prefers-color-scheme: dark) { .foot { background: #081421; color: var(--ink); } }

@media (max-width: 820px) {
  .hero { grid-template-columns: 1fr; }
  .vignette { max-width: 340px; }
}
```

- [ ] **Step 9: Run the tests and see them pass**

Run: `npm test`
Expected: `3` tests pass.

- [ ] **Step 10: Look at it in the browser**

Run: `npm run dev` and open http://localhost:8000.
- Expected: the navbar, the hero with the vignette, and 41 poems listed in three columns.
- Test the IT/EN switch.
- Stop the server when done.

- [ ] **Step 11: Commit**

```bash
git add package.json package-lock.json app public/css
git commit -m "Add Express app with home page, poem index and it/en switch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Leggo reading view

**Files:**
- Modify: `app/app.js` (add the `/leggo` routes before the 404 handler)
- Create: `app/views/leggo.ejs`
- Test: `app/tests/leggo.test.js`

**Interfaces:**
- Consumes: `data.poem(param)` and `data.index()` (Task 9), and the JSON item contract (Task 7).
- Produces: `GET /leggo` (redirects), `GET /leggo?n=<n>` (the selector redirect), and `GET /leggo/:n` (200, or 404 for an unknown poem).

- [ ] **Step 1: Write the failing `app/tests/leggo.test.js`**

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));
const byN = (n) => require(path.join(__dirname, '..', '..', 'public', 'data', `c${n}.json`));

test('every canto has a Leggo page', async () => {
  for (const p of index) {
    const res = await request(app).get(`/leggo/${p.n}`);
    assert.equal(res.status, 200, `canto ${p.roman}`);
  }
});

test("L'infinito renders all 15 verses exactly, numbered every 5", async () => {
  const n = index.find((p) => p.slug === 'l-infinito').n;
  const res = await request(app).get(`/leggo/${n}`);
  assert.match(res.text, /Sempre caro mi fu quest’ermo colle,/);
  assert.match(res.text, /Dell'ultimo orizzonte il guardo esclude\./);
  assert.match(res.text, /E il naufragar m’è dolce in questo mare\./);
  assert.equal((res.text.match(/<p class="verse/g) || []).length, 15);
  assert.match(res.text, /<span class="vn">5<\/span>/);
  assert.doesNotMatch(res.text, /<span class="vn">4<\/span>/);
  assert.match(res.text, /class="badge"/);
});

test('missing, unnumbered and speaker lines are visible', async () => {
  const consalvo = index.find((p) => p.slug === 'consalvo').n;
  let res = await request(app).get(`/leggo/${consalvo}`);
  assert.match(res.text, /<p class="verse missing" id="v130">/);
  const frag = index.find((p) => byN(p.n).stanzas.flat().some((i) => i.type === 'label')).n;
  res = await request(app).get(`/leggo/${frag}`);
  assert.match(res.text, /<p class="speaker">/);
  assert.match(res.text, /class="verse unnumbered"/);
});

test('bad poem addresses are 404, never 500', async () => {
  for (const bad of ['0', '42', 'abc', '12abc', '-1', '01', '1.5']) {
    const res = await request(app).get(`/leggo/${bad}`);
    assert.equal(res.status, 404, bad);
  }
});

test('selector and bare /leggo redirect to a known poem only', async () => {
  let res = await request(app).get('/leggo?n=12');
  assert.equal(res.headers.location, '/leggo/12');
  res = await request(app).get('/leggo?n=99');
  assert.equal(res.headers.location, `/leggo/${index[0].n}`);
  res = await request(app).get('/leggo');
  assert.equal(res.headers.location, `/leggo/${index[0].n}`);
});
```

- [ ] **Step 2: Run it and see it fail**

Run: `npm test`
Expected: the `leggo.test.js` tests FAIL with 404s. The `app.test.js` tests still pass.

- [ ] **Step 3: Add the routes to `app/app.js`**

Insert these directly after `app.get('/', …)`:

```js
app.get('/leggo', (req, res) => {
  const requested = data.poem(req.query.n);
  res.redirect(`/leggo/${requested ? requested.n : data.index()[0].n}`);
});

app.get('/leggo/:n', (req, res, next) => {
  const poem = data.poem(req.params.n);
  if (!poem) return next();
  res.render('leggo', { poem, title: `${poem.roman}. ${poem.title || poem.incipit}` });
});
```

- [ ] **Step 4: Write `app/views/leggo.ejs`**

```ejs
<%- include('partials/head') %>
<%- include('partials/nav') %>
<main class="wrap leggo">
  <form class="poem-select" action="/leggo" method="get">
    <label for="poem-select" class="eyebrow"><%= __('leggo.choose') %></label>
    <select id="poem-select" name="n" onchange="this.form.submit()">
      <% canti.forEach((p) => { %>
        <option value="<%= p.n %>"<%= p.n === poem.n ? ' selected' : '' %><%= p.status.leggo === 'none' ? ' disabled' : '' %>><%= p.roman %>. <%= p.title || p.incipit %></option>
      <% }) %>
    </select>
    <button type="submit"><%= __('leggo.go') %></button>
  </form>

  <article class="poem">
    <p class="badge"><%= __('leggo.source.' + poem.source.status) %></p>
    <h1 class="poem-head"><% poem.head.forEach((h) => { %><span><%= h %></span><% }) %></h1>
    <% if (poem.epigraph.length) { %>
      <blockquote class="epigraph"><% poem.epigraph.forEach((e) => { %><p><%= e %></p><% }) %></blockquote>
    <% } %>
    <% poem.stanzas.forEach((stanza) => { %>
      <div class="stanza">
        <% stanza.forEach((item) => { %>
          <% if (item.type === 'label') { %>
            <p class="speaker"><%= item.text %></p>
          <% } else {
               const cls = ['verse'];
               if (item.missing) cls.push('missing');
               if (item.unnumbered) cls.push('unnumbered');
               if (item.indent) cls.push('indent' + item.indent); %>
            <p class="<%= cls.join(' ') %>" id="<%= item.n ? 'v' + item.n : item.id %>"<%= item.unnumbered ? ' title="' + __('leggo.unnumbered') + '"' : '' %>><span class="vn"><%= item.n && item.n % 5 === 0 ? item.n : '' %></span><span class="vt"><% if (item.missing) { %><%= __('leggo.missingVerse') %><% } else { %><%- item.html %><% } %></span></p>
          <% } %>
        <% }) %>
      </div>
    <% }) %>
  </article>
</main>
<%- include('partials/footer') %>
```

`item.html` is printed unescaped. That's safe because `build_site_data._line_html` escapes all text and adds only `<em>` and `<sup class="noteref">`.

- [ ] **Step 5: Run the tests and see them pass**

Run: `npm test`
Expected: all 8 tests pass.

- [ ] **Step 6: Look at it in the browser**

Run: `npm run dev`. Open http://localhost:8000/leggo/12, /leggo/10 (indented terzine), /leggo/17 (verse 130 missing), /leggo/37 (speakers) and /leggo/27 (epigraph). Check phone width in the browser's device toolbar. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add app/app.js app/views/leggo.ejs app/tests/leggo.test.js
git commit -m "Add the Leggo verse reading view with poem selector

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Continuous integration

**Files:**
- Create: `.github/workflows/build.yml`

**Interfaces:**
- Consumes: the pipeline CLIs (Tasks 6–7), `npm test` (Tasks 9–10).
- Produces: a workflow that tests everything and commits regenerated `public/data/` when TEI or the pipeline change.

- [ ] **Step 1: Write `.github/workflows/build.yml`**

```yaml
name: build

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6

      - name: Pipeline tests
        working-directory: pipeline
        run: uv run pytest -q

      - name: Validate TEI
        working-directory: pipeline
        run: uv run python -m leggo_pipeline.validate

      - name: Build site data
        working-directory: pipeline
        run: uv run python -m leggo_pipeline.build_site_data

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - run: npm ci

      - run: npm test

      - name: Commit regenerated site data
        if: github.event_name == 'push'
        run: |
          if [ -n "$(git status --porcelain -- public/data)" ]; then
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add public/data
            git commit -m "Rebuild site data"
            git push
          fi
```

`uv run` reads `pipeline/.python-version` and installs Python 3.12 itself. Pushes made with the workflow's `GITHUB_TOKEN` don't trigger another workflow run, so this cannot loop.

- [ ] **Step 2: Check the workflow locally, the way CI runs it**

```bash
cd pipeline && uv run pytest -q && uv run python -m leggo_pipeline.validate && uv run python -m leggo_pipeline.build_site_data && cd .. && git status --porcelain -- public/data && npm ci && npm test
```

Expected:
- All steps pass.
- `git status` prints nothing: the committed JSON is already up to date, which shows the build is deterministic.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "Run pipeline tests, TEI validation and app tests in CI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: GitHub remote and Vercel deployment (checkpoints with the user)

**Files:**
- Create: `api/index.js`, `vercel.json`
- Test: a manual check of the deployed URL (commands below)

**Interfaces:**
- Consumes: the app from Tasks 9–10.
- Produces: a live preview URL and, after the user's OK, a production URL.

- [ ] **Step 1: Write `api/index.js`**

```js
// Vercel entry point: the whole Express app runs as one function.
module.exports = require('../app/app');
```

- [ ] **Step 2: Write `vercel.json`**

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }],
  "functions": {
    "api/index.js": { "includeFiles": "{app/**,public/data/**}" }
  }
}
```

- Vercel serves any file that exists in `public/` (CSS, image, JSON) before applying rewrites. Every other path goes to the Express function.
- `includeFiles` bundles the views, locales and JSON that `app/` reads with `fs`, so the function can find them.

- [ ] **Step 3: Check the entry point locally from a different directory**

Run: `node -e "const p=require('path').resolve('api/index.js'); process.chdir('/'); console.log(typeof require(p).handle)"`
Expected: `function`.

- [ ] **Step 4: Commit**

```bash
git add api/index.js vercel.json
git commit -m "Add Vercel entry point and function bundle config

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: CHECKPOINT: ask the user where the GitHub repository should live**

Ask for the owner or organisation (spec §12 open item) and whether the repository is private or public. Do not create anything before the user answers. Then run:

```bash
gh repo create <OWNER>/leggoleopardi --private --source . --remote origin --push
```

Replace `<OWNER>` with the user's answer, and use `--public` if they asked for public.

- [ ] **Step 6: CHECKPOINT: link and deploy a preview to Vercel**

`vercel link` is interactive. Ask the user to run `! npx vercel link` in this session and pick their team and a new project named `leggoleopardi`. Then deploy a preview:

Run: `npx vercel deploy`
Expected: it prints a preview URL, `https://leggoleopardi-<hash>.vercel.app`.

- [ ] **Step 7: Test the deployed URL**

```bash
URL=<preview URL from step 6>
curl -s -o /dev/null -w "%{http_code} /\n" "$URL/"
curl -s -o /dev/null -w "%{http_code} /leggo/12\n" "$URL/leggo/12"
curl -s -o /dev/null -w "%{http_code} /leggo/42\n" "$URL/leggo/42"
curl -s -o /dev/null -w "%{http_code} /css/site.css\n" "$URL/css/site.css"
curl -s -o /dev/null -w "%{http_code} /img/vignette-n35c-infinito.jpg\n" "$URL/img/vignette-n35c-infinito.jpg"
curl -s "$URL/leggo/12" | grep -c "Sempre caro mi fu quest’ermo colle,"
```

Expected:
- `200 /`
- `200 /leggo/12`
- `404 /leggo/42`
- `200 /css/site.css`
- `200 /img/vignette-n35c-infinito.jpg`
- `1`

If a preview is behind Vercel Deployment Protection (401), ask the user to open the URL in their browser, or to turn protection off for previews in the dashboard. Do not disable it yourself.

- [ ] **Step 8: CHECKPOINT: production deploy after the user approves**

Show the user the preview URL. The home-page image's rights are still an open item (spec §12), so ask whether it may appear on a public URL. Only after they say yes:

Run: `npx vercel deploy --prod`

Then repeat Step 7 against the production URL. Suggest to the user that they connect the GitHub repository in the Vercel dashboard (Project → Settings → Git), so every push to `main` deploys automatically. Phase 1a needs no environment variables.

---

## Self-review (done while writing)

- **Spec coverage (phase 1a):**
  - §4 layout and addressing: Tasks 1, 5 and 6.
  - §4.1 manifest keys: Task 5. `title_variants` and `witnesses` are created empty; they are filled in phase 1b.
  - §4.2 stable ids: Task 6, with its determinism test.
  - §4.3 fidelity: Tasks 2 and 6.
  - §5.1 harvest: Task 4.
  - §5.2 base text: Task 6.
  - §5.8 site data: Task 7.
  - §5.9 validation: Task 7. It uses the full `tei_all.rng`; the trimmed ODD schema comes later.
  - §6 Leggo without commentaries, plus home and it/en: Tasks 9–10.
  - §8 palette tokens: Task 9.
  - §9 tests, CI and deploy: Tasks 11–12.
  - Out of scope for 1a (spec §11 phase 1b): apparatus, commentaries, translations, concordance. The variant loci they need are already saved in `pipeline/work/loci/`.
- **Placeholders:** none in the code. The only values filled at run time are user decisions: the GitHub owner and the Vercel team.
- **Names are consistent across tasks:** `parse_pages`, `clean_inline`, `tokenize`, `WikiClient.page`, `follow_chain`, `load_manifest`, `build_poem_tei`, `validate`, `poem_json`, `build_site`, `data.index`, `data.poem`.
