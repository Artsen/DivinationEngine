# Rider–Waite–Smith 1909 corpus

This directory is the editable source of truth for the 78-card corpus. Each card file owns its
Waite interpretation records and explicitly Golden Dawn correspondence records. `sources.json`
and `traditions.json` resolve every knowledge claim; `images/manifest.json` resolves each card to
one public-domain Pamela Colman Smith image and records its dimensions and SHA-256.

## Source hierarchy

Waite text is attributed to the scan-backed 1922 Wikisource witness of *The Pictorial Key to the
Tarot* (first published in 1910). The recovery extraction from `ekelen/tarot-api` was a parsing
seed, not an authority. Corrections must be checked against the Wikisource transcription and its
page scan, preserve Waite's historical wording, and retain an exact section/card locator.

Golden Dawn correspondences come from the Book T material published as “A Description of the
Cards of the Tarot, with Their Attributions” in *The Equinox* I(8), 1912, pp. 143–210. These rows
always use the `golden-dawn` tradition and `tradition_specific` status. They are not intrinsic
properties of Waite's deck. The conservative 160-row set is retained because the recovery claim
of 180 could not be reconciled without making unsafe court-card equivalences.

Images are the original 1909 Roses & Lilies scan set credited to Pamela Colman Smith and scanner
Saskia Jansen on Wikimedia Commons. Individual file-page and direct-source URLs are retained.

## Authoring and stable keys

Files are ordered `00` through `77`; `sequence` is canonical deck order. Interpretation keys use
`waite-pk-<card>-<scope>`. Correspondence keys use `gd-<card>-<type>-<value>`. Keys identify
logical database rows and must not change for wording or locator corrections.

Run:

```console
divination-corpus validate data/corpus/tarot/rws-1909
divination-corpus build data/corpus/tarot/rws-1909
divination-corpus assets download data/corpus/tarot/rws-1909
divination-import data/corpus/tarot/rws-1909/build/rws-import.json --dry-run
divination-import data/corpus/tarot/rws-1909/build/rws-import.json
```

The asset command is resumable: existing files are verified, missing originals are downloaded,
and all hashes are recomputed. If Commons enforces its original-file quota, the downloader uses
the `gbox3d/talisman` GitHub copy only as a byte mirror; sampled files from the start and end of the
direct-download range were SHA-256-identical. Commons remains the canonical source and all mirror
files undergo dimension/hash validation. The build embeds image metadata in item metadata and
writes the generated importer bundle under `build/`.

## Corrections and future decks

Edit the smallest relevant card/source/image record, cite the exact witness boundary, then run the
validator, compiler, importer dry-run, and tests. Do not modernize source wording or infer missing
occult facts. Future decks should receive their own corpus directory, manifest, source registry,
traditions, card files, and image manifest; the compiler's Tarot invariants do not imply that RWS
interpretations or Golden Dawn mappings belong to another deck.
