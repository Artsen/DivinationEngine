# Yijing corpus

This directory contains the production, import-ready Yijing corpus. It is an algorithmic
domain corpus, not a `Collection`.

The top-level JSON files and 64 files under `hexagrams/` are reviewable authoring
records. `build/iching-import.json` is the generated import bundle containing eight
trigrams, the 64 King Wen hexagrams, 384 ordinary bottom-to-top lines, bilingual
received Chinese/James Legge core text and Wings, source locators, casting-method
records, and computed structural relationships.
`corrections.json` is the mandatory audit log. It records the gua-ci and ordinary-line
boundary repairs, Traditional Chinese identity corrections, and restoration of Legge's
source titles; no correction is applied silently.

`exact_text` means source-faithful textual content, not a byte-for-byte diplomatic
transcription. Extraction-platform Markdown links, HTML, images, and anchors are
removed while their visible textual content is retained. Whitespace and typographic
markup may be normalized. The pinned extraction revision remains available when the
platform-level Markdown itself must be inspected.

Legge gua-ci records retain Legge's hexagram name at the beginning of the source
statement. Modern pinyin from the extraction aid is identity metadata and does not
replace or silently remove Legge's wording. `source-integrity.json` records the
64-record gua-ci and 384-record ordinary-line boundary audits, the Traditional Chinese
identity-name audit, and the expanded source spot check.

## Provenance

- English: James Legge, *The Yî King*, Sacred Books of the East XVI (Oxford:
  Clarendon Press, 1882), checked against the scan-backed English Wikisource index.
- Traditional Chinese: the received `周易` text on Chinese Wikisource, manually
  collated with the Chinese Text Project witness.
- Extraction aid: `88-degrees/Book-of-Changes` at revision
  `4cecd53bb53aa10fc9a4c92ac30ce541724cd1ff`. Its
  Unlicense Markdown transcription retains Legge's SBE page anchors. It is never
  represented as the historical source in imported records.

The compiler handles documented transcription-shape irregularities only (for example,
a missing blockquote marker and an OCR `S.` used for numbered item `5.`). It does not
rewrite source prose. The source-integrity pass corrected a compiler boundary defect
that previously retained only the first physical source line of a multi-line gua-ci;
this was a parser correction, not an emendation to Legge. Any future textual correction
must be entered in `corrections.json` with the source, locator, before/after values, and
rationale.

## Commands

```bash
uv run divination-iching-corpus validate data/corpus/iching/legge-ctext
uv run divination-iching-corpus build data/corpus/iching/legge-ctext
uv run divination-import --dry-run data/corpus/iching/legge-ctext/build/iching-import.json
uv run divination-import data/corpus/iching/legge-ctext/build/iching-import.json
```

`acquire` deliberately uses GitHub's public API/raw endpoints and the MediaWiki API.
It does not scrape CTP, whose live site prohibits automated downloads.

## Casting and interpretation boundary

Patterns and positions are always bottom-to-top. Ordinary lines encode yin/yang only;
6/7/8/9 are outcomes of a particular cast. `用九` and `用六` are special text units,
never seventh lines.

The three-coin method records heads=3 and tails=2, with computed probabilities
1/8, 3/8, 3/8, 1/8. Its historical origin is intentionally not asserted. The yarrow
implementation performs three stalk manipulations per line using 49 working stalks,
six lines, and 18 persisted manipulations; 1/16, 5/16, 7/16, 3/16 is labeled as the
computational consequence of this reconstruction.

Context responses select judgments and Great Images for primary/relating figures plus
the ordinary texts and line Images for changing lines. No multi-changing-line school
rule is implemented.
