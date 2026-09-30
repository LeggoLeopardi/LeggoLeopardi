# LeggoLeopardi — design spec

Date: 2026-09-30 · Status: draft for review · Owner: Mariia

## 1. Purpose

LeggoLeopardi is a digital edition of Leopardi's *Canti*, modelled on LeggoManzoni: a reading text with historical commentaries, verse-aligned translations, collation of the printed witnesses and a concordance. It also gives the project team (PRIN "Leopardi e l'antico", DH.ARC / ADlab, Università di Bologna) a shared workspace for adding and revising materials.

Decisions from the meeting notes of 29 July and 1 September 2026 that this spec implements:

- *L'infinito* is the case study everything starts from.
- Mariia builds the infrastructure, including a "box" where the team can start depositing materials.
- The concordance must also search the genetic (manuscript) layer, with genetic hits shown in a different colour.
- Commentaries: Chiara Picardi (ADlab internship) digitises and OCRs them; Chiara Flori's list has 37 commented editions.
- Translations: Sofia Zecchini (EN/FR/DE, 19th century), Mariia (RU).
- Genetic encoding model: Carlotta Paci's *Alla primavera* (manuscript file + printed-witness file).

### Success criteria

1. Phase 1: *L'infinito* is complete in all four public modules (Leggo, Traduco, Collaziono, Concordanza) on a Vercel deploy, and all 41 Canti are readable with a provisional base text.
2. Phase 2: team members can log in, edit TEI and alignments, and publish approved versions to the public site without touching git.
3. The public site runs without a database, so it can later move to the UniBo server with `git pull && npm start`.

## 2. Decisions taken

| Topic | Decision |
|---|---|
| Scope | All ~41 Canti in one interface (like all chapters in LeggoManzoni); *L'infinito* first as the complete vertical slice, other poems gain layers as material arrives |
| Base (reading) text | **N35c**: the corrected copy of *Canti*, Napoli, Starita 1835. WikiLeopardi files all 41 Canti, including *Il tramonto della luna* and *La ginestra*, under N35c; the base witness is recorded per poem in `canti.json` so the team can correct it where needed |
| Base text source, now | **WikiLeopardi** N35c pages (all 41 Canti present), marked provisional |
| Base text source, later | The team's verified TEI (Priore/Nava, Paci) replaces WikiLeopardi poem by poem |
| v1 modules | Leggo, Traduco, Collaziono, Concordanza |
| Genetic edition | Our own implementation, designed later. **No EVT.** In v1 the genetic TEI is indexed for the concordance only |
| Codebase | Fresh repo, Express + EJS, pieces ported from LeggoManzoni. The old clone is kept as `../LeggoLeopardi_manzoni-ref/` for reference |
| Hosting | Vercel while developing; UniBo server later (public site only) |
| Storage | Postgres for users and drafts/versions; git for published files |
| UI languages | Italian and English. Poem titles stay in Italian |

## 3. Sources

| Layer | Source | State | Use |
|---|---|---|---|
| Base text, 41 Canti | WikiLeopardi (`wikileopardi.altervista.org/wiki_leopardi/api.php`), pages prefixed `N35c` (224 pages) | Clean `<poem>` blocks with numbered verses; titles inconsistent across pages | Harvested into `tei/base/` |
| Printed-witness apparatus | WikiLeopardi variant pages linked from highlighted words on each N35c page; witness chain in each page header (e.g. NR25 → B26 → F31 → N35 → N35c) | Attribution lives on the variant pages | Harvested into `tei/witnesses/` |
| Genetic TEI, 6 Idilli incl. *L'infinito* | `../evt-viewer-angular/src/assets/data/` (Priore, Nava): AN (layers), AV, NR25, B26, F31, N35, N35c | Parallel segmentation, verified | v1: concordance index only |
| *Alla primavera* | `../commenti/Alla Primavera_{MANOSCRITTO,STAMPE}.xml`, `Note alle Canzoni_STAMPE.xml` (Paci) | Verified; sigla typo `#N35C` at v.10 | Model for Canzoni; cross-check for the apparatus harvester |
| F31 TEI, 22 Canti | `../LeopardiTEIConversion/F31_works/` (Picardi) | Apparatus assigns unattributed variants to every other witness; IX missing | Reference only; not ingested |
| Translations EN/FR/DE | `../commenti/Zecchini_{Regno Unito,Francia,Germania} traduzioni.docx` (9 + 8 + 21 tables) | Transcribed; see §5.4 | Extracted into `tei/traduzioni/` |
| Translations RU, EN, FR, ES | `../leopardi_translations/data/texts/leopardi_*` | Poem-level only; many Wikisource copies; RU book transcriptions are uncollated OCR | Imported with provenance flags |
| Commentaries | `../commenti/*.pdf, *.djvu` (Straccali 1892 and 1919, Mestica, Fornaciari, Castagnola, Scherillo, Battistelli; Cappelletti has no text layer) | Not encoded | L'infinito notes extracted and corrected by hand |

## 4. Repository and data model

```
canti.json            manifest: one entry per poem
tei/                  published, canonical TEI (committed by Publish or by hand)
  base/cNN.xml          N35c reading text
  witnesses/cNN.xml     printed-witness apparatus (parallel segmentation)
  genetic/cNN.xml       manuscript TEI (indexed only in v1)
  commenti/<autore>/cNN.xml
  traduzioni/<lang>_<translator>_<year>/cNN.xml
pipeline/             Python build steps and tests
public/data/          generated JSON (committed, never edited by hand)
app/                  Express + EJS: public views, /workspace (phase 2)
docs/                 specs, plans, mockups
```

### 4.1 Manifest `canti.json`

One entry per poem, with:
- `n`: 1–41
- `roman`: the N35c numbering
- `slug`
- `title`
- `title_variants[]`: used to match titles from WikiLeopardi and the docx sources
- `base_witness`: `N35c`
- `witnesses[]`
- `wiki_pages[]`: the hand-checked list of WikiLeopardi page titles for this poem
- `status`: one flag per module, `none | provisional | verified`

Every list of poems in the app and pipeline is derived from this file; nothing is hard-coded.

### 4.2 Addressing

- Every word of the base text has a stable id `cNN.vV.wW`. For example, `c12.v3.w2` is canto XII, verse 3, word 2.
- Base TEI encodes `<lg>`, `<l n>` and `<w xml:id>`.
- Commentary notes point at the base text with `target` / `targetEnd` word ranges. This is the stand-off model of LeggoManzoni.
- Translation segments point at verses with `corresp="#c12.v1"`, or at a verse range when lines are merged, split, or the translation is prose.
- **Base ids never change.** When verified TEI replaces the WikiLeopardi text, the pipeline compares verse and word counts. It reports every id whose word changed or disappeared, and the replacement is blocked until the report is resolved.

### 4.3 Text fidelity

All texts are kept character for character as in the source: `’` stays `’`, and accents, spacing and typos stay as they are (for example Zecchini's *"vorbe reitet"*). Normalisation exists only as a separate search key inside the concordance, never in the stored text.

## 5. Pipeline (`pipeline/`, Python)

The pipeline runs locally or in CI. Each step reads files and writes files, and each step is idempotent.

### 5.1 `harvest_wikileopardi.py`

- Fetch the N35c pages and linked variant pages through the MediaWiki API.
- Send a browser-like User-Agent: the default Python agent gets 403.
- Rate-limit the requests.
- Cache the raw wikitext under `pipeline/cache/`, so rebuilds don't re-fetch.
- Use `canti.json` to group pages into poems.

### 5.2 `build_base.py`

- Parse the `<poem>` blocks: leading verse numbers, title and stanza breaks.
- Strip the wiki highlight markup (`<span style=…>`, `[[target|shown]]`) and keep the displayed text.
- Write `tei/base/cNN.xml` with `@source="WikiLeopardi"` and `@status="provisional"`.

### 5.3 `build_apparatus.py`

- For each highlighted link on an N35c page, read its variant page and extract each witness's reading.
- Write parallel segmentation `<app><lem wit="#N35c"><rdg wit="#…">`.
- A reading whose witness cannot be determined is written with `cert="low"` and added to the review list. It is never attributed to "all other witnesses".
- Cross-check the output against the matching verses of Paci's *Alla primavera* STAMPE file and the Priore/Nava *L'infinito*, and report any disagreements.

### 5.4 `extract_zecchini.py` (all 38 tables)

Each table has a header row and one content row: the Italian in cell 0 and the translation in cell 1, one paragraph per line. The two cells are independent text streams. Their line counts differ; for example, one German table has 1,216 lines of Italian and 1,186 of translation.

1. Read the heading paragraphs above each table for year, translator and bibliographic source. Read the header cell for the reference edition (N35c for most, 1831 for three German tables).
2. Split the Italian cell into poems by title lines and match them to cantos through `title_variants`. Plain keyword search is not enough: *"d'infinito affanno"* in *All'Italia* is not *L'infinito*.
3. Split the translation cell into poems. A title line is a short line without final punctuation that follows a blank line. Pair the translated poems with the Italian ones in order, and use LaBSE similarity where the order or count is off.
4. Propose verse alignment:
   - 1:1 when line counts match;
   - otherwise LaBSE grouping (1:2, 2:1);
   - prose paragraphs are aligned to verse ranges.
5. Write `tei/traduzioni/<lang>_<translator>_<year>/cNN.xml` with the alignment marked `@status="proposed"`.
6. Diff Zecchini's Italian against the WikiLeopardi base text and report each verse that differs.

### 5.5 `import_translations.py`

- Import every *L'infinito* translation from `leopardi_translations`: all Russian ones, plus Townsend, Aulard and the rest.
- Carry over the provenance and licence notes. This includes the "OCR, not yet collated" flag where present.
- Alignment is proposed in the same way as in §5.4.

### 5.6 `extract_commentaries.py`

- For the L'infinito pages of Straccali (1892, 1919), Mestica, Fornaciari, Castagnola and Scherillo, extract the existing text layer.
- Hand-correct the output. The OCR loses the long s (for example "pen iero"). Correction happens in the workspace, or by hand before phase 2 exists.
- Split the text into notes (lemma plus comment). Propose each note's `target` / `targetEnd` range by matching its lemma against the base text; a person confirms it.
- **No LLM calls** in the pipeline unless explicitly approved. If LLM-assisted OCR correction is wanted, estimate the cost first.

### 5.7 `build_concordance.py`

- Lemmatise with Stanza (Italian), as LeggoManzoni does.
- Each occurrence records `{form, lemma, canto, verse, witness, layer}`, where `layer` is `base`, `print` or `genetic`.
- The genetic entries come from `tei/genetic/`: for *L'infinito*, the AN/AV readings, including the readings of each revision layer.

### 5.8 `build_site_data.py`

- Write `public/data/cNN.json`: base text, apparatus rows, and the commentaries and translations whose status is confirmed.
- Also write `public/data/concordance.json` and `public/data/catalogue.json` (commentators, translations, witnesses).

### 5.9 `validate.py`

- Check each TEI file for well-formedness and against a trimmed TEI schema (ODD-derived RNG).
- Check that every `target`, `targetEnd` and `corresp` resolves to an existing id.
- Check that every poem in `canti.json` has a base file.
- The build fails on any error.

## 6. Public site (phase 1)

All pages share a poem selector listing all 41 Canti. A poem that has no data yet for the current module is shown greyed out, according to its `status`.

**Leggo** `/leggo/:canto`
- The N35c text laid out as verse: verse numbers every 5 lines, stanza breaks kept, the title as printed.
- 1–2 commentary side panels, with the commentator chosen from a list. Clicking a verse highlights its notes; clicking a note highlights its lemma span.
- A margin marker on verses that have printed variants, linking to Collaziono.
- A provenance badge (*provvisorio / verificato*).

**Traduco** `/traduco/:canto`
- The Italian plus 1–2 translations, aligned by verse. Rows follow the alignment groups, and prose translations sit as a block beside their verse range.
- Filter by language, translator and year.
- A card for each translation: source, reference edition and provenance.
- "All translations of this verse" mode.

**Collaziono** `/collaziono/:canto`
- A grid: rows are verses, columns are the poem's printed witnesses.
- Readings identical to N35c are faded; variant spans are highlighted.
- Toggle between all verses and only verses with variants.
- `cert="low"` readings are marked *attribuzione da verificare*.
- Manuscripts are not shown in v1.

**Concordanza** `/concordanza`
- A KWIC list searchable by form or lemma, filtered by poem, witness and layer.
- Hits are coloured by layer: base (ink), printed variant (blue), genetic (ochre).
- One JSON file, searched in the browser.

**Other pages:** home, Progetto (credits), Commenti and Traduzioni catalogues, it/en switch.

**Mobile:** Leggo and Traduco stack their panels. Collaziono shows one witness column at a time, with a picker.

**Only confirmed data appears on the public site.** Proposed alignments and unconfirmed notes stay in the workspace.

## 7. Team workspace (phase 2, outline)

`/workspace`, in the same Express app, requires login.

- **Accounts:** invite-only, email and password.
- **Roles:**
  - `admin`: users, publish;
  - `editor`: edit, approve, publish;
  - `contributor`: upload, edit drafts, confirm alignments.
- **Database (Postgres on Neon):**
  - `users`
  - `files` (path)
  - `file_versions`: content, author, timestamp, message, status `draft | approved | published`
  - `review_items`
  - `uploads`
- **Concurrent edits:** every save sends the version it was based on. If a newer version exists, the save is refused and a diff is shown, so nothing is silently overwritten.
- **TEI editor:** XML highlighting, validation on save (the same rules as `validate.py`), and a live preview in the Leggo layout.
- **Review queues:**
  - proposed alignments;
  - `cert="low"` apparatus readings;
  - commentary lemma ranges;
  - Zecchini-vs-WikiLeopardi verse differences.
- **Publish:** approved versions are written to `tei/` as one GitHub commit by a bot account; the commit message names the authors. CI rebuilds and Vercel redeploys.
- **Box:** uploads (scans, docx, PDF, notes) go to Vercel Blob, tagged by poem and type.

Phase 2 gets its own implementation plan. This section fixes only the storage and publish model so that phase 1 does not contradict it.

## 8. Visual identity

The site keeps LeggoManzoni's structure so the two read as sister projects: one main colour, two tints, a warm accent, paper ground, and Cormorant Garamond. Green is replaced by blue, at the professoressa's request.

Draft palette "Ocean v1" (mockup: `docs/mockups/home-ocean-v1.html`):

| Role | Hex |
|---|---|
| Main | `#2F6391` |
| Dark | `#0E3A62` |
| Tint | `#A9C8DB` |
| Panels | `#E6EFF6` |
| Accent | `#B8743A` |
| Paper | `#F7F4EA` |
| Concordance: printed variant | `#3479A7` |
| Concordance: genetic | `#B8743A` |

**Open:** a warmer variant of the palette is to be produced and compared before the palette is fixed.

**Home vignette:** page 62 of N35c with *L'infinito* (WikiLeopardi image), toned blue. The preferred alternative is the AN autograph from the Biblioteca Nazionale di Napoli, but the IIIF links in the EVT TEI currently return a server error and need refreshing. The reproduction rights of whichever image is used must be confirmed before public launch.

Both light and dark themes are supported.

## 9. Testing, build and deployment

**Pipeline tests (pytest), with *L'infinito* as the fixture:**
- 15 verses; text identical to a checked snapshot, character for character.
- Word ids are stable across rebuilds.
- The apparatus contains the known variant loci: v.3 *Dell'ultimo*, vv.4–5 *interminati ‖ Spazi*, v.7 *fingo;*, v.13 *il suon*, v.14 *Immensità*, v.15 *il naufragar*. Each has witness attribution taken from its variant page.
- The Zecchini extractor finds the tables that contain *L'infinito* and does not match *"d'infinito affanno"*.

**App tests:**
- Every route returns 200 for every poem in `canti.json`.
- Missing layers render "in preparazione" and never an error.

**CI:**
- A GitHub Action runs the pipeline, `validate.py` and the tests on every push that touches `tei/`, `canti.json` or `pipeline/`.
- It commits the regenerated `public/data/`. Vercel and UniBo therefore never need Python.

**Vercel:**
- Deploys from `main`, with preview deploys for branches.
- Secrets live in the Vercel dashboard only: `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `GITHUB_BOT_TOKEN`, `SESSION_SECRET`. `.env` is gitignored from the first commit.
- Test the deployed URL after each deploy.

**UniBo later:** `git pull && npm start` serves the public site. The workspace stays on Vercel.

## 10. Porting from LeggoManzoni

| Port (adapted) | Leave behind |
|---|---|
| Visual structure, navbar, Cormorant Garamond | Chapter lists hard-coded in routes and scripts |
| i18n setup (it/en), locale file structure | Request-time XSLT (`convert.js`) |
| Stand-off `target`/`targetEnd` model | V27/Q40 two-witness collation code |
| Idea of offline-built collation and concordance | 795 MB of PDFs, videos and news pages in the repo |
| Commentary side-panel and translation-pair interactions | Duplicate CSS, dead views, `*_old` directories |

The concordance filter and KWIC client logic may be adapted from `concordanza.js`, but prose-specific code (commas, chapters) is removed.

## 11. Phases

1. **Phase 1a, skeleton:** repo, `canti.json`, harvester and base text for all 41 Canti, Leggo without commentaries, Vercel deploy.
2. **Phase 1b, *L'infinito* complete:** apparatus and Collaziono, Zecchini and RU translations with Traduco, commentaries in Leggo, Concordanza with genetic layer.
3. **Phase 1c, other poems:** apparatus and translations for the rest (as the pipeline allows), catalogues and Progetto page.
4. **Phase 2, workspace:** accounts, versions, editor, review queues, publish, box.
5. **Later:** our own genetic-edition view, facsimile viewer (Vedo), commentaries beyond the scanned set, replacement of WikiLeopardi texts with the team's TEI.

## 12. Open items

- Warmer palette variant; final palette choice with the professoressa.
- Home vignette: refresh the BNN autograph links, and confirm image rights (BNN, WikiLeopardi).
- Confirm with Priore/Nava/Paci that the WikiLeopardi text may be shown provisionally, with credit.
- Check that the Sofia Zecchini EN/FR/DE files on the Drive match the docx files used here (the meeting notes mention 56 translations; the docx files hold 38 tables).
- Moroncini 1917 (digitised at ADlab) is not in the local folder. Obtain it.
- GitHub organisation or account for the new remote and bot.
