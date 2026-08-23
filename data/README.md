# Curated data

This directory is for manually curated, repeatable import bundles. External claims must retain a
`source` reference and exact quoted source text belongs only in `exact_text`. The importer
is transactional: malformed documents, unresolved references, and constraint violations
roll back the whole bundle.

Imports are idempotent upserts and never synchronize deletions. Stable identities are collection
slug, `collection-slug/item-slug`, tradition slug, source key, interpretation key, and
correspondence key. Changing one of these creates a different logical record; correct content by
keeping its key and editing its other fields.

Generate the authoritative JSON Schema with:

```bash
divination-import --schema > import-schema.json
divination-import examples/demo-import.json --dry-run
```

`examples/demo-import.json` is deliberately fictional and must not be treated as canonical.

Curated, independently editable corpora live under `corpus/`. Generated importer bundles remain
inside each corpus's `build/` directory so authoring records never collapse into a single opaque
source file. The first production corpus is documented in `corpus/tarot/rws-1909/README.md`.
