# LeggoLeopardi: project status

Last updated: 2026-09-30.

## Live

- Site: https://leggoleopardi.vercel.app. Vercel project `mary-levs-projects/leggoleopardi`, deployed from the CLI with `npx vercel deploy --prod`.
- Code: https://github.com/LeggoLeopardi/LeggoLeopardi. CI runs on every push and pull request.
- Automatic deploys from GitHub start once the Vercel GitHub app is given access to the LeggoLeopardi organisation.

## Phases (spec §11)

| Phase | State |
|---|---|
| 1a Skeleton: N35c base text of all 41 Canti from WikiLeopardi, Leggo view, CI, deploy | **Done** (PR #1, 2026-09-30) |
| 1b *L'infinito* complete: apparatus and Collaziono, translations and Traduco, commentaries in Leggo, Concordanza | Next |
| 1c Other poems | – |
| 2 Team workspace | – |

## Decisions taken while building phase 1a

- **Harvest cache.** The cache was first filled with pages fetched on 2026-09-30. Delete `pipeline/cache/` to fetch everything again.
- **Tokenizer.** Combining accents (decomposed input such as `di` + U+0300) stay with their letter.
- **Validator.** Duplicate ids are reported by name and do not stop the other checks (`collect_ids=False`).
- **Broken page chains** on the wiki stop the build with an error naming the poem:
  - a page with no forward link;
  - a `#REDIRECT` page.
- **Language.** With no `lang` cookie, the site follows the browser's `Accept-Language`, so English browsers see English. Italian is the default otherwise.
- **Fragment XXXVII** has 3 speaker labels after verse 1 (MELISSO, ALCETA, MELISSO), as the wiki has them.
- **Line roles.** The lines before verse 1 are title lines, except for these poems, set in `canti.json` → `pre_roles`:
  - 27 and 32: epigraph plus attribution;
  - 34: Greek epigraph plus attribution;
  - 37: speaker.

## To review with the team (from `reports/base_report.md`)

- *Consalvo* v.130 is missing on WikiLeopardi. It is shown as "verso mancante nella fonte".
- XXXVII: *"Egli ci ha tante stelle,"* has no verse number (it is a half-verse split between two speakers).
- There are no stanza markers on the wiki for four poems, so each comes out as one stanza:
  - *Il primo amore*: correct, the terzine are continuous.
  - *La sera del dì di festa*, *Il sogno*, *Dal greco di Simonide*: to check.

## Open items

- **Palette.** The team chooses at the 2026-09-30 meeting: Ocean v1, Mare al tramonto, Petrolio e ocra or Indaco e seppia (`docs/mockups/palettes-warm-v1.html`). To apply it, replace the `:root` colour block in `public/css/site.css` and its dark-mode version.
- **Image rights** for the home vignette (N35c p. 62, image from WikiLeopardi). The BNN autograph is the preferred alternative, but its IIIF links in the EVT TEI currently return errors.
- **Zecchini translations.** The meeting notes mention 56 translations; the docx files hold 38 tables. Check whether the Drive has more.
- **Moroncini 1917** was digitised at ADlab and is not in the local folder.

## Deferred fixes (found in the final review of phase 1a)

- **Must be in place before the team's TEI replaces the WikiLeopardi text:** compare the new word ids with the committed ones and block the replacement if any change (spec §4.2).
- A verse found out of order after a later verse is shown as missing, even though the wiki has it. The report should say that it exists.
- There is no Express error handler. A malformed URL gets Express's default 400 page, and a missing JSON file would fail every request.
- A wiki page deleted after `canti.json` was generated raises an error that does not name the poem.
- CI grants `contents: write` to pull-request runs too. Limit it to push.
- On a phone, the sticky navbar wraps to about 4 rows.
- There is no favicon.
