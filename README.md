# DivinationEngine

DivinationEngine is a standalone, provenance-first backend for digital divination. The
current milestone performs mechanical collection draws, data-driven spread placement, and
traditional six-throw three-coin I Ching casts. It persists readings and source-backed
knowledge. **It does not provide AI-generated readings or fabricate symbolic meaning.**

## Architecture

- `backend/app/domain`: pure casting mechanics and an injectable randomness protocol.
- `backend/app/services`: reading orchestration and transactional structured imports.
- `backend/app/db`: SQLAlchemy persistence models, separate from domain values/functions.
- `backend/app/api`: versioned HTTP transport only.
- `backend/alembic`: the production schema migration history.
- `data`: import documentation and explicitly fictional examples.

A Reading owns any number of immutable collection or I Ching casts. A collection cast owns
unique draw results; orientation is recorded on each result. Placement is separate and may
reference a persisted spread position or custom coordinates. Knowledge records reference a
Source and may reference a Tradition. Correspondence types are open strings rather than
columns, so new systems do not require schema changes.

SQLite is the default. PostgreSQL can replace it by setting `DIVINATION_DATABASE_URL`; the
domain layer has no database dependency. UUID strings are public identifiers.

## Install and run

Python 3.12 or newer is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Swagger is at `http://127.0.0.1:8000/docs`. Configuration uses environment variables with
the `DIVINATION_` prefix, notably `DIVINATION_DATABASE_URL`.

## Example workflow

```bash
curl -X POST http://127.0.0.1:8000/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"slug":"test-deck","name":"Test Deck","system_type":"oracle","supports_reversals":true}'

curl -X POST http://127.0.0.1:8000/api/v1/collections/COLLECTION_ID/items \
  -H "Content-Type: application/json" -d '{"slug":"alpha","name":"Alpha"}'

curl -X POST http://127.0.0.1:8000/api/v1/readings \
  -H "Content-Type: application/json" -d '{"title":"Example","question":"What is present?"}'

curl -X POST http://127.0.0.1:8000/api/v1/readings/READING_ID/casts/draw \
  -H "Content-Type: application/json" \
  -d '{"collection_id":"COLLECTION_ID","count":1,"reversals_enabled":true}'

curl -X POST http://127.0.0.1:8000/api/v1/readings/READING_ID/casts/iching
curl http://127.0.0.1:8000/api/v1/readings/READING_ID/context
```

Cast results have no update or delete endpoint by design. Retrieving a reading loads stored
results and never casts again. I Ching pattern strings and throw arrays are bottom-line first;
changing lines are numbered 1 through 6 from bottom to top.

## Bulk data curation

Run `divination-import data/examples/demo-import.json` after migrating. The importer validates
the complete Pydantic document and all cross-references in one transaction. Its source keys and
`collection-slug/item-slug` references are stable within the import file; database UUIDs are
generated during import. Run `divination-import --schema` for its JSON Schema.

The demo bundle is fictional. Do not insert inferred, generated, or unattributed meaning.
Exact source language must remain in `exact_text`, distinct from locators and curator notes.

## Quality checks

```bash
pytest
ruff format --check .
ruff check .
mypy
```

## Scope and roadmap

This milestone includes the API, migrations, secure mechanical casts, persistent readings,
notes, spreads/placements, provenance-aware item knowledge, and bulk import. Future milestones
may add a web UI, authentication, richer hexagram corpora, more collection systems, and an AI
client. Any future AI remains a consumer of the public facts API—not a truth source and not part
of casting.
