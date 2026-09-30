# LeggoLeopardi

Digital edition of Giacomo Leopardi's *Canti* (DH.ARC, Università di Bologna), sister project of LeggoManzoni.
Reading text: N35c (the corrected copy of *Canti*, Napoli, Starita 1835). Current transcription: WikiLeopardi, provisional.

## Build the data (Python 3.12 via uv)

    cd pipeline
    uv run python -m leggo_pipeline.manifest          # (re)build canti.json from WikiLeopardi
    uv run python -m leggo_pipeline.build_base        # tei/base/*.xml + reports/base_report.md
    uv run python -m leggo_pipeline.build_facsimile   # L'infinito: page images, verse zones (tei/facsimile), reports/facsimile_report.md
    uv run python -m leggo_pipeline.build_translations # tei/traduzioni from pipeline/traduzioni.json (needs ../commenti, ../leopardi_translations)
    uv run python -m leggo_pipeline.validate          # TEI checks
    uv run python -m leggo_pipeline.build_site_data   # public/data/*.json
    uv run pytest

## Run the site (Node 22)

    npm install
    npm run dev        # http://localhost:8000
    npm test

Design spec: `docs/superpowers/specs/2026-09-30-leggoleopardi-design.md`. Current status, decisions and open items: `docs/status.md`.
