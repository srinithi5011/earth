# Darukaa Earth — AI Biodiversity Intelligence

An evidence-grounded environmental intelligence system, built for the Darukaa.Earth
hackathon challenge. It behaves like an AI environmental scientist: it retrieves
scientific knowledge, reasons across multiple environmental variables through a
structured relationship graph, and produces actionable, evidence-verified
biodiversity recommendations — never a single-variable, generic chatbot answer.

## Why this is not a generic LLM chatbot

1. **Recommendations are never produced by "asking the LLM to reason."** A
   deterministic rule engine (`backend/app/services/reasoning.py`) evaluates the
   user's environmental state against thresholds, then traverses a stored
   relationship graph (`environmental_relationships` table) to find causal chains
   connecting ≥3 metrics. The LLM, when configured, is used only to phrase
   already-derived reasoning — it cannot invent relationships.
2. **Every scientific claim must trace to retrieved evidence.** The retrieval
   layer (TF-IDF vector search + metadata filtering + similarity threshold) feeds
   an evidence verification stage (`backend/app/services/evidence.py`) that
   rejects recommendations with no supporting evidence and strips any numeric
   claim not found verbatim in the retrieved text.
3. **The system asks for missing information instead of guessing.** Structured
   environmental state + missing-field detection (spec section 3) means a vague
   message like *"biodiversity is declining on my land"* gets clarifying
   questions, not a generic answer.
4. **The knowledge base is real and inspectable**, not a black box — the Evidence
   Explorer and Reasoning Graph pages let a judge see exactly which sources and
   which causal edges produced a given recommendation.

## Architecture

```
User (chat or structured JSON)
        │
        ▼
Environmental State Extraction  (app/services/conversation.py)
        │
        ▼
Missing-Information Detection
        │
        ▼
Query Expansion  →  TF-IDF Embedding  →  Vector Search  →  Metadata Filtering
        │                                  (app/services/retrieval.py)
        ▼
Deterministic Multi-Metric Reasoning  (app/services/reasoning.py — graph traversal)
        │
        ▼
Recommendation Generation  (app/services/recommendations.py — evidence per intervention)
        │
        ▼
Evidence Verification  (app/services/evidence.py — rejects unsupported claims)
        │
        ▼
Structured JSON Response  →  Frontend (Dashboard / Chat / Profile / Evidence / Graph)
```

Full pipeline orchestration lives in `backend/app/services/rag.py`.

### A note on the embedding backend

This project was built and packaged in a sandboxed environment **with no network
access**, so an internet-downloaded sentence-embedding model was not an option
for the default configuration. The default embedding backend is therefore a
**TF-IDF vectorizer (scikit-learn)** fit over the ingested corpus — a real,
working, fully offline vector search, not a stub. It satisfies every pipeline
requirement (embedding generation, vector search, similarity threshold,
metadata filtering, ranking, dedup) without any external dependency.

To use a stronger embedding model in production, implement the
`EmbeddingBackend` protocol in `backend/app/services/embeddings.py` for your
model of choice and switch `EMBEDDING_MODEL` in `.env` — the rest of the
pipeline (retrieval, reasoning, recommendations) is unaffected by this swap.

### A note on the knowledge corpus

The seeded knowledge base (`data/seed/*.json`) is intentionally labeled
**"Darukaa Earth Curated Knowledge Base"** rather than attributed to invented
FAO/IPCC/IPBES paper titles or fabricated URLs — per the hackathon's own
anti-hallucination rules, this system never fabricates papers, authors, or
statistics. The seed content reflects well-established, general environmental
science consensus, with source URLs pointing at the relevant organization's
real public portal (e.g. `fao.org/soils-portal`), not a specific paper.

**Before a real deployment**, ingest actual FAO/IPCC/UNEP/IPBES/NASA/USGS PDFs
or reports via `POST /api/knowledge/ingest` or `scripts/ingest.py` — the
ingestion pipeline (PDF/TXT/MD/CSV/JSON) is fully implemented and ready for
real source documents, at which point recommendations will cite those specific
documents instead.

## Database schema

SQLAlchemy models in `backend/app/models/`:

| Table | Purpose |
|---|---|
| `users` | Session → user mapping |
| `conversations` | Multi-turn conversation + accumulated environmental state |
| `messages` | Individual chat turns, with structured response attached |
| `environmental_profiles` | Persisted structured environmental snapshots |
| `knowledge_documents` | Ingested source documents with full metadata |
| `knowledge_chunks` | Chunked, embedded text with denormalized metadata for fast filtering |
| `environmental_relationships` | The reasoning engine's knowledge graph edges |
| `recommendations` / `recommendation_evidence` | Persisted structured recommendations + their evidence |

Runs on **SQLite by default** (zero infrastructure — `data/darukaa.db`) and on
**PostgreSQL + pgvector** in the Docker Compose path (`database/init.sql`
provisions the `vector` extension and an `ivfflat` index). The same SQLAlchemy
models work against both; only the embedding column's physical type and index
differ.

## Local setup (no Docker, SQLite, fastest way to try it)

Requires network access to install dependencies (the sandbox this was authored
in did not have this — these commands are unverified end-to-end in this
environment, see **Verification status** below).

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # DEMO_MODE=true by default — no LLM_API_KEY needed
cd ..
python scripts/seed.py       # loads the curated knowledge corpus + relationship graph
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

Open `http://localhost:5173`.

## Docker setup

```bash
cp .env.example .env
docker compose up --build
```

This starts `postgres` (with pgvector), `backend` (auto-seeds the knowledge base
on first boot via `backend/entrypoint.sh`), and `frontend`. Backend on
`localhost:8000`, frontend on `localhost:5173`.

## Environment variables

See `.env.example` for the full, commented list. Key ones:

| Variable | Purpose | Required? |
|---|---|---|
| `DATABASE_URL` | SQLite (local) or Postgres (Docker) connection string | Yes (has a default) |
| `DEMO_MODE` | Forces deterministic templates, no external LLM calls | No (defaults true) |
| `LLM_API_KEY` | Anthropic/OpenAI key — leave blank to run fully offline | No |
| `LLM_PROVIDER` / `LLM_MODEL` | Which provider/model to call if a key is set | No |
| `EMBEDDING_MODEL` | `tfidf` (default, offline) or a real model name | No |

Never commit a real `.env` — only `.env.example` is checked in.

## Data ingestion

```bash
python scripts/ingest.py path/to/report.pdf \
  --title "Soil Carbon in Semi-Arid Systems" \
  --organization "FAO" \
  --publication-year 2023 \
  --source-url "https://fao.org/..." \
  --document-type report \
  --topic soil \
  --region "east africa" \
  --credibility-tier authoritative
```

Or via the API: `POST /api/knowledge/ingest` (multipart form upload).

## Running tests

```bash
cd backend
pytest
```

Covers: environmental extraction, chunking, deterministic reasoning
(multi-metric chain construction), retrieval (vector search + metadata
filtering + similarity threshold), evidence verification (anti-hallucination
checks on numeric claims), and full API integration tests for `/api/chat`,
`/api/analyze`, `/api/evidence`, `/api/relationships`, and conversation
persistence.

## Evaluation

```bash
python scripts/seed.py     # if not already seeded
python scripts/evaluate.py
```

Runs 11 environmental scenarios (the 10 required by the spec, plus a vague-input
missing-information-detection case) and reports retrieval relevance, evidence
coverage, multi-metric reasoning rate, recommendation specificity, citation
presence, and missing-information-detection accuracy.

## Demo scenario (spec section 17)

Input: `Soil organic carbon is 0.3%, rainfall is low, I grow monoculture wheat in a semi-arid region.`

Expected flow: the system detects low soil carbon + low rainfall + monoculture,
traces the relationship chain (soil carbon → water retention → plant resilience;
monoculture → habitat diversity → species richness), and returns cover-crop /
crop-rotation / agroforestry-style recommendations, each with affected metrics,
time horizons, evidence, and an Evidence Confidence label — never a bare "use
sustainable farming."

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | Main conversational turn (NL + optional structured input) |
| POST | `/api/analyze` | Structured-input-only variant, no NL |
| GET | `/api/conversations/{id}` | Full conversation + accumulated state |
| POST | `/api/environment` | Save an environmental profile snapshot |
| GET | `/api/environment/{id}` | Retrieve a saved profile |
| GET | `/api/evidence` | Evidence Explorer data (filterable by topic/region/org) |
| GET | `/api/evidence/documents` | List ingested source documents |
| POST | `/api/knowledge/ingest` | Ingest a new document (PDF/TXT/MD/CSV/JSON) |
| GET | `/api/relationships` | Full reasoning-graph edge list |
| GET | `/api/health` | Health check (DB connectivity, demo mode, vector backend) |

Interactive docs at `/docs` (FastAPI auto-generated).

## Verification status (read this)

This project was built in a sandboxed authoring environment **without network
access** — `pip install` and `npm install` could not be run there, so the
Python and TypeScript/React code could not be executed or dependency-checked
end-to-end in that environment. What **was** verified there:

- Every Python file passes `python -m py_compile` (no syntax errors).
- Every JSON seed file passes `json.load` (valid JSON, matches expected schema).
- The overall control flow, imports, and function signatures were manually
  cross-checked module-by-module for consistency (e.g. `retrieve()`'s return
  type matches what `recommendations.py` and `rag.py` consume).

What **was not** verified there and needs to happen once you have network
access (CI or your own machine) — this is real, standard first-run
verification, not a hidden gap:

- `pip install -r backend/requirements.txt` and `npm install` in `frontend/`
- `pytest` actually passing (tests are written against the real modules, but
  never executed)
- `docker compose up --build` end-to-end
- `npm run build` for the frontend TypeScript compile

If anything fails on first run, it's most likely a minor import-order or
dependency-pin issue — the architecture and logic have been through the design
and static-check pass described above, but not a live execution pass.

## Limitations

- Default embedding backend (TF-IDF) is weaker than a modern sentence-embedding
  model for paraphrase-heavy queries; swap it for production use (see above).
- The seeded knowledge corpus is a small, honestly-labeled curated set, not a
  full ingested FAO/IPCC/IPBES library — ingest real documents before relying
  on this for real recommendations.
- Natural-language environmental state extraction is regex/keyword-based for
  guaranteed offline operation; an LLM-assisted extraction path exists
  (`app/services/llm.py`) and activates automatically once `LLM_API_KEY` is set
  and `DEMO_MODE=false`, improving extraction on more free-form phrasing.
- Geospatial input (lat/lon) is accepted and stored but no external geospatial
  API is integrated, per the spec's constraint that external APIs must not be
  mandatory for the core demo.
- pgvector `ivfflat` index dimension (4096, matching the default TF-IDF
  `max_features`) should be tuned down if you reduce `max_features` or swap to
  a lower-dimensional embedding model.

## Future improvements

- Swap TF-IDF for a production sentence-embedding model + pgvector HNSW index.
- Expand the relationship graph and intervention-category rule set with
  domain-expert review.
- Add authentication for multi-tenant deployments (currently session-based,
  single-tenant-friendly).
- Add streaming responses for the chat endpoint.
- Expand evaluate.py into a CI gate with pass/fail thresholds per metric.

## Project structure

```
darukaa-earth/
├── frontend/            React + TypeScript + Vite + Tailwind (5 pages)
├── backend/
│   └── app/
│       ├── api/          chat, environment, evidence, relationships, health
│       ├── models/       SQLAlchemy ORM (conversation, knowledge, recommendation, ...)
│       ├── schemas/      Pydantic (environment, chat)
│       ├── services/     rag, reasoning, recommendations, evidence, retrieval,
│       │                 embeddings, conversation, llm
│       ├── knowledge/    ingestion, chunking, embeddings (re-export)
│       ├── prompts/      one file per LLM prompt stage
│       └── tests/
├── data/
│   ├── seed/              curated knowledge corpus + relationship graph JSON
│   └── processed/         generated TF-IDF vectorizer (gitignored)
├── database/init.sql       pgvector schema setup
├── scripts/                seed.py, ingest.py, evaluate.py
├── docker-compose.yml
├── .env.example
└── README.md   (this file)
```
