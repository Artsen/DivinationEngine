# Elder Futhark corpus

This is a reviewable, provenance-backed corpus for the canonical 24-character Elder Futhark.
It is a historical writing-system corpus, not an ancient oracle manual. The application draws
from a finite 24-item bag without replacement, using secure operating-system randomness, but
that workflow is explicitly `derived` software behavior.

## Historical layers

- `runes/*.json` holds normalized identities. Every Proto-Germanic name and lexical value is
  marked as a scholarly reconstruction. Kenaz, Perthro, Algiz, and Laguz carry additional
  editorial caution; this is not asserted as a universal count of disputed runes.
- `rune-poems.json` holds 29 Old English, 16 Norwegian, and 16 Icelandic source-language
  stanzas. The Old English poem belongs to Anglo-Saxon Futhorc; the Scandinavian poems belong
  to Younger Futhark. They are relationships to Elder Futhark items, not definitions of them.
- `editorial-translations.json` holds 61 newly written modern-English renderings. These are
  explicitly derived, machine-assisted project editorial text, not historical exact text and
  not divinatory meaning. Originals, translations, translation notes, and lexical sources have
  separate fields in authoring data, persistence, API context, and the UI. See
  [TRANSLATION_NOTES.md](TRANSLATION_NOTES.md) for method and difficult readings.
- Ac, Æsc, Yr, Iar, and Ear remain legitimate unmapped Futhorc records. They never become
  canonical Elder Futhark items.
- `attestations.json` distinguishes complete rows, recognized 24-rune rows whose surviving
  inscriptions are damaged, partial rows, and contextual evidence. Its `legible_rune_items`,
  `inferred_rune_items`, and `uncertain_rune_items` are mutually exclusive epigraphic claims.
  A rune file's `attestation_refs` is only a relationship join and is never, by itself, proof
  that the rune is visible. Built item metadata replaces those bare joins with structured
  `attestation_evidence`, and generated correspondences carry the per-rune evidence status.
  Kylver G 88 is a complete-row witness while retaining a note about epigraphic variation.
  RuneS classifies Vadstena's inscription as incomplete, and its transcription marks uncertain
  characters. Grumpan witnesses the row tradition, but its transcription contains uncertain
  and supplied positions. Svingerud is context only, not a complete row.
- `divination-methods.json` distinguishes Tacitus's marked wooden lots from the application's
  finite-bag mechanic. Tacitus does not identify Elder Futhark, runes, 24 pieces, rune stones,
  reversals, or modern spreads.
- `modern-traditions.json` keeps the blank rune, reversal practices, and Armanen material in
  later bibliographic/history layers. No copyrighted modern interpretation prose is included.

The three groups of eight are structural. Popular deity-based ætt names are not asserted.
The canonical collection has no blank rune and does not support reversals.

## Exact-text and rights policy

The only exact textual bodies committed here are the 61 historical source-language rune-poem
stanzas transcribed in fixed Wikisource revision `10795428` (2 January 2021). Their historical
texts are public domain; the digital witness and locator are recorded on every stanza. Unicode character names are licensed data,
not historical text.

Bruce Dickins's 1915 edition is retained as bibliography and a locator only. Wikisource marks
the edition public domain in the United States, but Dickins died in 1978, so the corpus does
not claim worldwide public-domain status and bundles zero Dickins translations. The bundled
English is new DivinationEngine editorial text, prepared from the originals with registered
public-domain Bosworth-Toller, Cleasby-Vigfusson, and Zoëga lexical aids. Dickins was used only
after drafting for a source-likeness sanity check. No text from Ralph Blum, modern guidebooks,
modern website translations, copyrighted scholarship, or Guido von List is reproduced.

## Validate, build, and import

```console
divination-rune-corpus validate data/corpus/runes/elder-futhark
divination-rune-corpus build data/corpus/runes/elder-futhark
divination-import data/corpus/runes/elder-futhark/build/elder-futhark-import.json --dry-run
divination-import data/corpus/runes/elder-futhark/build/elder-futhark-import.json
```

Build output is deterministic and lives under `build/`. Imports are transactional,
idempotent upserts: absent authoring records never imply deletion. Stable keys such as
`runes/elder-futhark/01` and `elder-futhark/fehu` are external identities.

Later traditions can be added with their own source and tradition records, without changing
canonical identities or enabling behavior on this historical collection.
