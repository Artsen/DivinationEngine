# DivinationEngine

DivinationEngine is a local, provenance-first application for digital divination. Its React
workspace is a client of a FastAPI backend that performs mechanical Tarot draws, I Ching
casts, and Elder Futhark rune draws, persists exact results, and returns source-backed knowledge. **It does not provide
AI-generated readings or fabricate symbolic meaning.**

## Architecture

- `backend/app/domain`: pure casting mechanics and an injectable randomness protocol.
- `backend/app/services`: reading orchestration and transactional structured imports.
- `backend/app/db`: SQLAlchemy persistence models, separate from domain values/functions.
- `backend/app/api`: versioned HTTP transport only.
- `backend/alembic`: the production schema migration history.
- `frontend`: React, Vite, and TypeScript browser client; no divination mechanics.
- `data`: import documentation and explicitly fictional examples.

A Reading owns any number of immutable collection or I Ching casts. A collection cast owns
unique draw results and belongs to a persisted deck session; orientation is recorded on each
result. Placement is separate and may
reference a persisted spread position or custom coordinates. Knowledge records reference a
Source and may reference a Tradition. Correspondence types are open strings rather than
columns, so new systems do not require schema changes.

SQLite is the default. PostgreSQL can replace it by setting `DIVINATION_DATABASE_URL`; the
domain layer has no database dependency. UUID strings are public identifiers.

## Install and run the application

Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js 22+ are required. The bootstrap
command applies migrations and idempotently installs the bundled RWS, I Ching, and Elder
Futhark corpora. It
never deletes existing readings or other user data and is safe to run again.

```console
uv sync --extra dev
uv run divination-dev-bootstrap
```

Then run two terminals from the repository root.

Terminal 1 — API:

```console
uv run uvicorn app.main:app --app-dir backend --reload
```

Terminal 2 — browser client:

```console
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies relative `/api/v1/...`
requests to `http://127.0.0.1:8000`; set `VITE_API_PROXY_TARGET` to change that development
target. A production deployment can set `VITE_API_BASE_URL` at build time without editing
source. No permissive cross-origin policy is required for the normal proxy setup.

The app reports when the API is unavailable or when any individual corpus is missing. Corpus installation
is never triggered by the browser. Configuration uses environment variables with the
`DIVINATION_` prefix, notably `DIVINATION_DATABASE_URL`; set it before bootstrap and server
startup to use a database other than the default `divination.db`.

Swagger remains available at `http://127.0.0.1:8000/docs` for API development.

### Development bootstrap

`divination-dev-bootstrap` explicitly performs two operations:

1. upgrades the selected database to the latest Alembic revision;
2. transactionally upserts `rws-import.json`, `iching-import.json`, and
   `elder-futhark-import.json`.

Its JSON report distinguishes created and updated rows. There is intentionally no implicit or
destructive reset mode.

### OpenAPI client types

The checked-in OpenAPI snapshot and generated TypeScript declarations make frontend builds
independent of a running backend. Refresh both after changing API contracts:

```console
uv run divination-openapi frontend/openapi.json
cd frontend
npm run api:types
```

## Example workflow

The web UI is the primary human workflow. The following curl sequence remains useful for API
development and integration debugging.

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

### Deck sessions

Omitting `deck_session_id` from a draw creates a fresh session backed by the full collection.
This preserves the original behavior: independent fresh casts may draw the same item. Every
collection cast response includes its `deck_session_id`. Pass that ID on a later draw in the
same Reading and Collection to continue from the remaining unseen items:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/readings/READING_ID/casts/draw \
  -H "Content-Type: application/json" \
  -d '{"collection_id":"COLLECTION_ID","count":1,"deck_session_id":"SESSION_ID"}'
```

Availability is derived from persisted draw results. A session cannot cross Reading or
Collection boundaries, cannot redraw a consumed item, and fails cleanly when fewer than the
requested number remain. Returning cards, cuts, piles, and partial reshuffles are intentionally
deferred.

## Bulk data curation

Run `divination-import data/examples/demo-import.json` after migrating. Imports are transactional
and idempotent upserts. Collections use `slug`; items use `collection-slug/item-slug`; sources,
interpretations, and correspondences use required curator-controlled `key` values; traditions use
`slug`. Rerunning a bundle updates those logical records without changing UUIDs or deleting rows
that disappeared from the file. Stable keys are external identities and should not be casually
renamed.

Validate the schema with `divination-import --schema`. Exercise all reference resolution and DB
constraints without retaining changes with:

```bash
divination-import data/examples/demo-import.json --dry-run
```

### Corpus authoring

The tracked Rider–Waite–Smith corpus is under `data/corpus/tarot/rws-1909`. It keeps per-card
authoring records, provenance registries, and canonical public-domain image metadata separate from
the generated importer bundle. Validate or rebuild it with:

```console
divination-corpus validate data/corpus/tarot/rws-1909
divination-corpus build data/corpus/tarot/rws-1909
```

Missing canonical assets can be fetched reproducibly with `divination-corpus assets download`.
The corpus README documents its source hierarchy, rights, correction workflow, stable keys, and
the deliberate separation between Waite and Golden Dawn traditions.

The production Yijing corpus is under `data/corpus/iching/legge-ctext`. It remains an
algorithmic domain (64 hexagrams, 384 ordinary lines, and eight trigrams), not a generic
Collection. Zhouyi core, Tuan, Xiang, Wenyan, Xici, Shuo Gua, Xu Gua, Za Gua, Legge
commentary, and casting-method layers remain separate and carry per-record locators.

```console
divination-iching-corpus validate data/corpus/iching/legge-ctext
divination-import data/corpus/iching/legge-ctext/build/iching-import.json --dry-run
```

I Ching cast requests accept `{"method":"three-coin"}` or
`{"method":"yarrow-stalk"}`. Omitting the body preserves the three-coin default.

The Elder Futhark authoring corpus is under `data/corpus/runes/elder-futhark`. It contains
exactly 24 canonical items and keeps reconstructed Proto-Germanic identities, later rune-poem
systems, archaeological attestations, historical lot divination, and modern occult history in
separate layers.

```console
divination-rune-corpus validate data/corpus/runes/elder-futhark
divination-rune-corpus build data/corpus/runes/elder-futhark
divination-import data/corpus/runes/elder-futhark/build/elder-futhark-import.json --dry-run
```

The canonical collection has three structural groups of eight, no blank rune, and no
reversals. Familiar names are scholarly reconstructions rather than surviving Elder Futhark
manuscript labels; uncertainty remains explicit. The Old English poem belongs to Anglo-Saxon
Futhorc, while the Norwegian and Icelandic poems belong to Younger Futhark. Their texts are
related historical evidence—not universal ancient meanings.

Tacitus describes marked wooden lots, but does not identify the marks as Elder Futhark or
runes and does not describe the application's 24-item bag. The finite-bag, draw-without-
replacement method is therefore documented as derived software behavior. Later systems such
as Armanen and modern blank-rune/reversal practices can be added as separately sourced
traditions without rewriting canonical identities.

All 61 historical source-language poem stanzas are present. Exact Dickins English translations
are intentionally omitted: the 1915 edition is public domain in the United States, but Dickins
died in 1978, so the project does not make a blanket worldwide-public-domain claim. No modern
guidebook interpretation prose is bundled. See the corpus README for the exact-text source and
redistribution audit.

An unknown reference or constraint violation rolls back the entire import, including updates
performed earlier in that bundle.

The demo bundle is fictional. Do not insert inferred, generated, or unattributed meaning.
Exact source language must remain in `exact_text`, distinct from locators and curator notes.

## Reading context and provenance

`GET /api/v1/readings/{id}/context` returns facts grouped under each actual draw result. Each
result contains `applicable_interpretations`, `other_interpretations`, and correspondences.
Sources and traditions are complete, deduplicated lookup maps at the response root, so every
provenance identifier can be resolved without another request. The endpoint never generates an
interpretation.

The deterministic relevance rule is:

- upright: `upright`, `divinatory`, `symbolism`, `description`, `commentary`;
- reversed: `reversed`, `symbolism`, `description`, `commentary`;
- no orientation: `divinatory`, `symbolism`, `description`, `commentary`.

All other stored categories remain visible under `other_interpretations`; new taxonomy values are
never silently declared relevant.

Canonical RWS images are delivered offline through
`GET /api/v1/items/{item_id}/image`. The endpoint accepts only an existing item identity,
cross-checks its metadata against the committed RWS image manifest, and never accepts a file
path. Attested images receive immutable cache headers; unknown, non-RWS, missing, or altered
asset records return 404.

## Taxonomy policy

Content classifications are open taxonomies. `Collection.system_type` and
`Interpretation.interpretation_type` accept lowercase slug-like values, with `tarot`, `oracle`,
`runes` and the documented interpretation types treated as known conventions rather than a closed
database list. This permits future sourced systems and categories without migrations.

Controlled engine states remain closed because they carry behavioral invariants. These include
cast type, draw orientation, and correspondence attestation status. Adding a new casting strategy
or workflow state therefore requires an intentional engine and schema change.

## Quality checks

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv lock --check
uv run alembic check
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
npm run e2e
```

## Scope and roadmap

This milestone includes the browser reading workspace, API, migrations, secure mechanical
casts, persistent readings, notes, basic spread/placement display, provenance-aware knowledge,
and bulk import. Future milestones may add richer spread editing, authentication, additional
rights-compatible corpora, or packaging. Any future AI remains a consumer of the public facts
API—not a truth source and not part of casting.
