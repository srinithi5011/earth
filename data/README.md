# data/

- `seed/` — the curated knowledge corpus (`soil_health.json`, `biodiversity.json`,
  `climate.json`, `human_impact.json`) and the environmental relationship graph
  (`relationships.json`), loaded by `scripts/seed.py`. See the root README's
  "A note on the knowledge corpus" section for sourcing/attribution details.
- `documents/` — drop raw source files here (PDF/TXT/MD/CSV/JSON) before running
  `scripts/ingest.py path/to/file` to add them to the knowledge base.
- `processed/` — generated artifacts (the fitted TF-IDF vectorizer). Gitignored;
  regenerated automatically by `scripts/seed.py` / ingestion.
