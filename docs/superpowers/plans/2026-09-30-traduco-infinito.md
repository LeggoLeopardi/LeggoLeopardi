# Traduco for L'infinito: implementation plan

**Goal:** Show every translation of *L'infinito* we have (about 20, in EN, FR, DE, ES and RU) next to the Italian text on a new `/traduco/12` page. The poem and the translation sit side by side, each with its own line breaks. There is no verse-to-verse alignment yet; that comes after the admin panel.

**Spec:** `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`, §5.4, §5.5 and §6 (Traduco).

## Decisions taken with the user on 2026-09-30

- **Alignment:** whole poem side by side now (A). Verse-by-verse alignment, confirmed by a person, comes later in the admin panel (B).
- **Rights:** show every translation, including Akhmatova 1967, which is in copyright. The rights note is kept in each file and in `docs/status.md`.
- **No explanatory text on the page.** The source of each translation sits in a collapsed line.

## What the sources look like

- **Zecchini's docx files.** The translation column of 9 tables contains *L'infinito*. The poem runs from its title line (*L'infini*, *Das Unendliche*, *The infinite*, *L'infinito*) up to the next poem's title.
  - Bouché-Leclercq is prose.
  - Amiel's line breaks were lost in the docx, so the whole poem is one paragraph.
  - De Montlaur's block opens with the Italian line *"E il naufragar m'è dolce in questo mare."*
- **`leopardi_translations/data/texts/leopardi_l_infinito/*.txt`.** Eleven texts: Townsend, the anonymous Spanish text, Oyuela, Aulard (prose), Sainte-Beuve, Lacaussade, Vernier, Akhmatova, Ivanov, Pomyan and Tkhorzhevsky.
  - The metadata comes from `reports/inventory_leopardi.csv` and the TEI headers.
  - The first line of the anonymous Spanish text (*"Véase también: El infinito"*) is Wikisource navigation, not part of the translation. It falls outside the extracted range.
- **Duplicates.**
  - Sainte-Beuve appears in both sources, and the text is the same apart from non-breaking spaces before `:` and `;`. It becomes one translation with two sources; the text shown is Zecchini's transcription.
  - Cliffe 1893 and Cliffe 1896 differ (revised wording). They stay two versions.

## Design

- **`pipeline/traduzioni.json`** is a hand-checked config. For each poem it lists every translation with:
  - its id (`{lang}_{translator}_{year}`), language, translator, year, title and bibliographic reference;
  - its form (`verse` or `prose`) and a rights note;
  - its source, as either `{docx, table, start, end}` in paragraph indices or `{txt, start, end}` in line indices;
  - optional `title_lines`, extra `sources` and `notes`.

  Paths are relative to the parent `leopardi/` folder, which is present only locally.
- **`leggo_pipeline/translations.py`:**
  - `read_block()` returns the lines of a source range exactly as they are.
  - `split_block()` separates the title lines from the text and splits the text into stanzas at blank lines.
  - `build_translation_tei()` writes `tei/traduzioni/{id}/c{n}.xml` with `<div type="translation" xml:lang>`, `<head>`, `<lg><l>` for verse or `<p>` for prose, and a header holding the translator, date, bibl, sources and availability.
  - The CLI is `python -m leggo_pipeline.build_translations` and writes `reports/translations_report.md`, which lists the notes to review.
- **`build_site_data`** writes `public/data/trad/c{n}.json` from the TEI. It holds the Italian base stanzas and the translations sorted by language then year, and sets `status.traduco`.
- **App:**
  - `/traduco` redirects to the first poem that has translations.
  - `/traduco/:n?t=&t2=` shows the Italian and one translation, or two.
  - The translation pickers are grouped by language and submit on change; a button appears only in `<noscript>`.
  - Each translation's source sits in a collapsed `<details>`.
  - A poem without translations gives 404, and an unknown `t` falls back to the first translation.
  - The navbar's *Traduco* becomes a link.
  - Columns stack on phones.

## Tasks (TDD, one commit each)

1. **Translation extraction and TEI.**
   - Tests use a synthetic docx built with python-docx, a synthetic txt, and a schema-validated TEI.
   - A test on the real sources is skipped when they're absent (they aren't in CI).
2. **Config and build** for the 20 translations of *L'infinito*. Check the first and last line of each, then commit the TEI and the report.
3. **Site JSON** (`trad/c12.json`) and `status.traduco`.
4. **App:** route, view, pickers, navbar link and CSS. Then a browser check on desktop and on a phone.
5. **Docs** (`README.md`, `docs/status.md`), pull request, CI, merge and deploy.
