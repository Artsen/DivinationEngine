# Curated data

This directory is for manually curated import bundles. External claims must retain a
`source` reference and exact quoted source text belongs only in `exact_text`. The importer
is transactional: malformed documents, unresolved references, and constraint violations
roll back the whole bundle.

Generate the authoritative JSON Schema with:

```bash
divination-import --schema > import-schema.json
```

`examples/demo-import.json` is deliberately fictional and must not be treated as canonical.
