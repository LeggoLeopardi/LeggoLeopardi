# LeggoLeopardi: conventions

- Texts are kept character for character as in the source: never change `’`/`'`, accents, spelling or endings; never normalise Unicode. The only allowed normalisation is trimming/collapsing whitespace.
- Ids never change once published: `c{n}`, `c{n}.v{v}`, `c{n}.v{v}.w{k}`, `c{n}.v{v}.u{j}`. Commentaries and translations point at them.
- Every list of poems comes from `canti.json`; never hard-code poem numbers or titles.
- The pipeline makes no LLM or paid API calls unless the user approves the cost first.
- WikiLeopardi: cache every page in `pipeline/cache/`, browser-like User-Agent, 0.5 s between requests.
- Python: `cd pipeline && uv run …` (3.12). Node 22. The app never reads files relative to the working directory.
- `public/data/` and `tei/base/` are generated: change the pipeline, not the output.
- Spec: `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`. Plans: `docs/superpowers/plans/`.
