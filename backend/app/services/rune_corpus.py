from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.services.importer import (
    ImportBundle,
    ImportCollection,
    ImportCorrespondence,
    ImportInterpretation,
    ImportSource,
)


class RuneManifest(BaseModel):
    format_version: Literal["1"] = "1"
    slug: Literal["elder-futhark"]
    name: str
    description: str
    system_type: Literal["runes"] = "runes"
    supports_reversals: Literal[False] = False
    canonical_count: Literal[24] = 24
    groups: Literal[3] = 3
    items_per_group: Literal[8] = 8
    identity_source: str


class RuneSystem(BaseModel):
    key: str
    name: str
    layer: str
    canonical_count: int | None = None
    source_refs: list[str]
    notes: str | None = None


class RuneRecord(BaseModel):
    key: str = Field(pattern=r"^runes/elder-futhark/[0-9]{2}$")
    slug: str
    normalized_label: str
    row_position: int = Field(ge=1, le=24)
    aett: int = Field(ge=1, le=3)
    position_in_aett: int = Field(ge=1, le=8)
    glyph: str = Field(min_length=1, max_length=2)
    code_point: str = Field(pattern=r"^U\+[0-9A-F]{4,6}$")
    unicode_name: str
    transliteration: str
    sound_value: str
    proto_germanic_name: str
    reconstruction_status: Literal["reconstructed"]
    lexical_reconstruction: str
    name_evidence_status: Literal["reconstructed", "disputed"]
    uncertainty_notes: str | None = None
    source_refs: list[str]
    poem_refs: list[str]
    attestation_refs: list[str]


class RunePoemStanza(BaseModel):
    key: str
    poem: Literal["old-english", "norwegian", "icelandic"]
    system: Literal["anglo-saxon-futhorc", "younger-futhark"]
    sequence: int = Field(ge=1)
    rune_character: str
    normalized_name: str
    language: str
    original_text: str = Field(min_length=1)
    latin_tag: str | None = None
    source: str
    locator: str
    rights_status: str
    english_exact_text: str | None = None
    elder_futhark_item: str | None = None
    mapping_status: Literal["direct", "likely-related", "not-applicable"]
    mapping_justification: str


class Attestation(BaseModel):
    key: str
    name: str
    kind: Literal["complete-row", "full-row-with-damage", "partial-row", "contextual"]
    row_completeness: Literal[
        "complete", "intended-complete-survives-with-damage", "partial", "contextual"
    ]
    date: str | None = None
    object_id: str | None = None
    source_refs: list[str]
    transcription: str | None = None
    legible_rune_items: list[str]
    inferred_rune_items: list[str]
    uncertain_rune_items: list[str]
    notes: str


RuneEvidenceStatus = Literal["directly-legible", "inferred", "damaged-or-uncertain"]


def _rune_evidence_status(attestation: Attestation, rune_key: str) -> RuneEvidenceStatus | None:
    if rune_key in attestation.legible_rune_items:
        return "directly-legible"
    if rune_key in attestation.inferred_rune_items:
        return "inferred"
    if rune_key in attestation.uncertain_rune_items:
        return "damaged-or-uncertain"
    return None


class LoadedRuneCorpus(BaseModel):
    root: Path
    manifest: RuneManifest
    sources: list[ImportSource]
    traditions: list[dict[str, Any]]
    systems: list[RuneSystem]
    runes: list[RuneRecord]
    poems: list[RunePoemStanza]
    attestations: list[Attestation]
    divination_methods: list[dict[str, Any]]
    modern_traditions: list[dict[str, Any]]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_corpus(root: Path) -> LoadedRuneCorpus:
    return LoadedRuneCorpus(
        root=root,
        manifest=RuneManifest.model_validate(_read_json(root / "manifest.json")),
        sources=[ImportSource.model_validate(row) for row in _read_json(root / "sources.json")],
        traditions=_read_json(root / "traditions.json"),
        systems=[RuneSystem.model_validate(row) for row in _read_json(root / "rune-systems.json")],
        runes=[
            RuneRecord.model_validate(_read_json(path))
            for path in sorted((root / "runes").glob("*.json"))
        ],
        poems=[RunePoemStanza.model_validate(row) for row in _read_json(root / "rune-poems.json")],
        attestations=[
            Attestation.model_validate(row) for row in _read_json(root / "attestations.json")
        ],
        divination_methods=_read_json(root / "divination-methods.json"),
        modern_traditions=_read_json(root / "modern-traditions.json"),
    )


def _duplicates(values: Sequence[str | int]) -> list[str]:
    return sorted(str(value) for value, count in Counter(values).items() if count > 1)


def validate_corpus(corpus: LoadedRuneCorpus) -> dict[str, int]:
    errors: list[str] = []
    runes = corpus.runes
    poems = corpus.poems
    source_keys = {row.key for row in corpus.sources}
    tradition_slugs = {row["slug"] for row in corpus.traditions}
    system_keys = {row.key for row in corpus.systems}
    rune_keys = {row.key for row in runes}
    poem_keys = {row.key for row in poems}
    attestation_keys = {row.key for row in corpus.attestations}

    if corpus.manifest.supports_reversals:
        errors.append("canonical Elder Futhark collection cannot support reversals")

    if len(runes) != 24:
        errors.append(f"expected 24 canonical Elder Futhark runes, found {len(runes)}")
    if sorted(row.row_position for row in runes) != list(range(1, 25)):
        errors.append("rune row positions must be exactly 1-24")
    expected_groups = [(position - 1) // 8 + 1 for position in range(1, 25)]
    if [row.aett for row in sorted(runes, key=lambda row: row.row_position)] != expected_groups:
        errors.append("runes must form three consecutive groups of eight")
    if [row.position_in_aett for row in sorted(runes, key=lambda row: row.row_position)] != [
        position for _ in range(3) for position in range(1, 9)
    ]:
        errors.append("positions inside each aett must be exactly 1-8")
    for label, values in (
        ("rune key", [row.key for row in runes]),
        ("rune slug", [row.slug for row in runes]),
        ("rune glyph", [row.glyph for row in runes]),
        ("rune code point", [row.code_point for row in runes]),
        ("poem key", [row.key for row in poems]),
        ("source key", [row.key for row in corpus.sources]),
        ("system key", [row.key for row in corpus.systems]),
        ("attestation key", [row.key for row in corpus.attestations]),
    ):
        duplicates = _duplicates(values)
        if duplicates:
            errors.append(f"duplicate {label}: {', '.join(duplicates)}")

    if corpus.manifest.identity_source not in source_keys:
        errors.append("manifest identity source is not registered")
    required_systems = {"elder-futhark", "anglo-saxon-futhorc", "younger-futhark"}
    if not required_systems.issubset(system_keys):
        errors.append("Elder Futhark, Anglo-Saxon Futhorc, and Younger Futhark are required")
    for rune in runes:
        for source in rune.source_refs:
            if source not in source_keys:
                errors.append(f"{rune.key}: unknown source {source}")
    for system in corpus.systems:
        for source in system.source_refs:
            if source not in source_keys:
                errors.append(f"{system.key}: unknown source {source}")
    for attestation in corpus.attestations:
        for source in attestation.source_refs:
            if source not in source_keys:
                errors.append(f"{attestation.key}: unknown source {source}")
    for attestation in corpus.attestations:
        evidence_groups = (
            attestation.legible_rune_items,
            attestation.inferred_rune_items,
            attestation.uncertain_rune_items,
        )
        evidence_items = [item for group in evidence_groups for item in group]
        for rune_item in evidence_items:
            if rune_item not in rune_keys:
                errors.append(f"{attestation.key}: unknown rune item {rune_item}")
        duplicate_evidence = _duplicates(evidence_items)
        if duplicate_evidence:
            errors.append(
                f"{attestation.key}: rune evidence statuses overlap: "
                f"{', '.join(duplicate_evidence)}"
            )
        evidence_set = set(evidence_items)
        if attestation.kind in {"complete-row", "full-row-with-damage"}:
            if evidence_set != rune_keys:
                errors.append(
                    f"{attestation.key}: a 24-rune row witness must classify every rune item"
                )
        elif evidence_items:
            errors.append(
                f"{attestation.key}: partial/contextual records cannot imply per-rune evidence"
            )
        if attestation.kind == "complete-row":
            if attestation.row_completeness != "complete":
                errors.append(f"{attestation.key}: complete row has inconsistent completeness")
            if set(attestation.legible_rune_items) != rune_keys or (
                attestation.inferred_rune_items or attestation.uncertain_rune_items
            ):
                errors.append(
                    f"{attestation.key}: complete row must classify all 24 runes as legible"
                )
        if attestation.kind == "full-row-with-damage":
            if attestation.row_completeness != "intended-complete-survives-with-damage":
                errors.append(f"{attestation.key}: damaged row has inconsistent completeness")
            if not attestation.transcription:
                errors.append(f"{attestation.key}: damaged row must retain its transcription")
            if not (attestation.inferred_rune_items or attestation.uncertain_rune_items):
                errors.append(
                    f"{attestation.key}: damaged row must identify inferred or uncertain runes"
                )
        expected_non_row_completeness = {
            "partial-row": "partial",
            "contextual": "contextual",
        }
        if (
            attestation.kind in expected_non_row_completeness
            and attestation.row_completeness != expected_non_row_completeness[attestation.kind]
        ):
            errors.append(f"{attestation.key}: non-row record has inconsistent completeness")
    for rune in runes:
        expected_key = f"runes/elder-futhark/{rune.row_position:02d}"
        if rune.key != expected_key:
            errors.append(f"{rune.key}: expected stable key {expected_key}")
        if ord(rune.glyph) != int(rune.code_point[2:], 16):
            errors.append(f"{rune.key}: glyph and code point disagree")
        for poem_ref in rune.poem_refs:
            if poem_ref not in poem_keys:
                errors.append(f"{rune.key}: unknown poem {poem_ref}")
        for attestation_ref in rune.attestation_refs:
            if attestation_ref not in attestation_keys:
                errors.append(f"{rune.key}: unknown attestation {attestation_ref}")
                continue
            attestation = next(row for row in corpus.attestations if row.key == attestation_ref)
            if _rune_evidence_status(attestation, rune.key) is None:
                errors.append(
                    f"{rune.key}: attestation {attestation_ref} lacks per-rune evidence status"
                )
    rune_refs_by_key = {row.key: set(row.attestation_refs) for row in runes}
    for attestation in corpus.attestations:
        evidence_items = (
            attestation.legible_rune_items
            + attestation.inferred_rune_items
            + attestation.uncertain_rune_items
        )
        for rune_key in evidence_items:
            if rune_key in rune_refs_by_key and attestation.key not in rune_refs_by_key[rune_key]:
                errors.append(
                    f"{attestation.key}: {rune_key} evidence lacks reciprocal attestation reference"
                )

    counts = Counter(row.poem for row in poems)
    expected_poems = {"old-english": 29, "norwegian": 16, "icelandic": 16}
    if dict(counts) != expected_poems:
        errors.append(f"poem counts must be {expected_poems}, found {dict(counts)}")
    mapped = [row for row in poems if row.elder_futhark_item]
    expansions = [row for row in poems if row.mapping_status == "not-applicable"]
    if len(mapped) != 56:
        errors.append(f"expected 56 poem mappings, found {len(mapped)}")
    if {row.normalized_name for row in expansions} != {"Ac", "Æsc", "Yr", "Iar", "Ear"}:
        errors.append("the five Futhorc expansion stanzas must remain unmapped")
    if any(row.elder_futhark_item not in rune_keys for row in mapped):
        errors.append("poem mapping references an unknown Elder Futhark item")
    if any(row.mapping_status == "not-applicable" and row.elder_futhark_item for row in poems):
        errors.append("not-applicable poem records cannot map to Elder Futhark items")
    for poem in poems:
        if poem.source not in source_keys:
            errors.append(f"{poem.key}: unknown source {poem.source}")
        if poem.system not in tradition_slugs:
            errors.append(f"{poem.key}: unknown tradition {poem.system}")
        if not poem.original_text.strip():
            errors.append(f"{poem.key}: missing original-language stanza")

    canonical_blob = json.dumps([row.model_dump() for row in runes], ensure_ascii=False).lower()
    suspicious = [
        "manifestation",
        "soulmate",
        "chakra",
        "crystal",
        "aura",
        "career success",
        "divine masculine",
        "divine feminine",
        "moon phase",
        "merkstave",
        "reversed meaning",
        "odin rune",
        "wyrd rune",
    ]
    leaked = [term for term in suspicious if term in canonical_blob]
    if leaked:
        errors.append(f"modern/divinatory claim leakage in canonical records: {', '.join(leaked)}")
    if any("blank" in row.slug.lower() or "blank" in row.normalized_label.lower() for row in runes):
        errors.append("canonical Elder Futhark must not contain a blank rune")
    if errors:
        raise ValueError("Rune corpus validation failed:\n- " + "\n- ".join(errors))

    return {
        "runes": len(runes),
        "aett_groups": len({row.aett for row in runes}),
        "reconstructed_names": sum(row.reconstruction_status == "reconstructed" for row in runes),
        "caution_records": sum(row.name_evidence_status == "disputed" for row in runes),
        "old_english_stanzas": counts["old-english"],
        "norwegian_stanzas": counts["norwegian"],
        "icelandic_stanzas": counts["icelandic"],
        "stanzas": len(poems),
        "original_language_bodies": sum(bool(row.original_text.strip()) for row in poems),
        "english_exact_texts": sum(row.english_exact_text is not None for row in poems),
        "english_omitted": sum(row.english_exact_text is None for row in poems),
        "poem_mappings": len(mapped),
        "direct_mappings": sum(row.mapping_status == "direct" for row in poems),
        "cautious_mappings": sum(row.mapping_status == "likely-related" for row in poems),
        "unmapped_expansions": len(expansions),
        "attestations": len(corpus.attestations),
        "complete_row_witnesses": sum(row.kind == "complete-row" for row in corpus.attestations),
        "damaged_row_witnesses": sum(
            row.kind == "full-row-with-damage" for row in corpus.attestations
        ),
        "legible_rune_links": sum(len(row.legible_rune_items) for row in corpus.attestations),
        "inferred_rune_links": sum(len(row.inferred_rune_items) for row in corpus.attestations),
        "uncertain_rune_links": sum(len(row.uncertain_rune_items) for row in corpus.attestations),
    }


def build_bundle(corpus: LoadedRuneCorpus) -> ImportBundle:
    validate_corpus(corpus)
    items = []
    interpretations: list[ImportInterpretation] = []
    correspondences: list[ImportCorrespondence] = []
    poems_by_item: dict[str, list[RunePoemStanza]] = {}
    attestations_by_key = {row.key: row for row in corpus.attestations}
    for poem in corpus.poems:
        if poem.elder_futhark_item:
            poems_by_item.setdefault(poem.elder_futhark_item, []).append(poem)

    for rune in sorted(corpus.runes, key=lambda row: row.row_position):
        item_ref = f"elder-futhark/{rune.slug}"
        attestation_evidence = []
        for attestation_key in rune.attestation_refs:
            attestation = attestations_by_key[attestation_key]
            evidence_status = _rune_evidence_status(attestation, rune.key)
            if evidence_status is None:
                continue
            attestation_evidence.append(
                {
                    "key": attestation.key,
                    "name": attestation.name,
                    "row_classification": attestation.kind,
                    "row_completeness": attestation.row_completeness,
                    "rune_evidence_status": evidence_status,
                    "transcription": attestation.transcription,
                }
            )
        items.append(
            {
                "slug": rune.slug,
                "name": rune.normalized_label,
                "display_name": f"{rune.glyph} {rune.normalized_label}",
                "sequence": rune.row_position,
                "symbol": rune.glyph,
                "metadata": rune.model_dump(exclude={"poem_refs", "attestation_refs"})
                | {
                    "system": "elder-futhark",
                    "poem_refs": rune.poem_refs,
                    "attestation_evidence": attestation_evidence,
                },
            }
        )
        for suffix, type_, value, source, status, notes in (
            (
                "reconstructed-name",
                "reconstructed_name",
                rune.proto_germanic_name,
                rune.source_refs[0],
                rune.name_evidence_status,
                rune.uncertainty_notes,
            ),
            (
                "lexical",
                "lexical_reconstruction",
                rune.lexical_reconstruction,
                rune.source_refs[0],
                rune.name_evidence_status,
                rune.uncertainty_notes,
            ),
            (
                "sound",
                "historical_sound_value",
                rune.sound_value,
                rune.source_refs[0],
                "reconstructed",
                "Sound value represented as a scholarly reconstruction.",
            ),
            (
                "unicode",
                "unicode_identity",
                f"{rune.code_point} — {rune.unicode_name}",
                "unicode-runic-names-list",
                "attested",
                "Modern Unicode character identity; not an ancient rune name witness.",
            ),
        ):
            correspondence_status = (
                "attested"
                if suffix == "unicode"
                else ("disputed" if status == "disputed" else "reconstructed")
            )
            correspondences.append(
                ImportCorrespondence(
                    key=f"elder-futhark-{rune.row_position:02d}-{suffix}",
                    item=item_ref,
                    type=type_,
                    value=value,
                    tradition="proto-germanic-reconstruction" if suffix != "unicode" else None,
                    source=source,
                    status=correspondence_status,
                    locator="Older Futhark chart" if suffix != "unicode" else rune.code_point,
                    notes=notes,
                )
            )
        correspondences.append(
            ImportCorrespondence(
                key=f"elder-futhark-{rune.row_position:02d}-structural-group",
                item=item_ref,
                type="aett_group",
                value=f"Group {rune.aett}, position {rune.position_in_aett}",
                tradition="elder-futhark",
                source="barnes-2012-runes-handbook",
                status="attested",
                locator="Elder Futhark organization",
                notes=(
                    "Structural group of eight. Later popular deity-based group names are "
                    "not asserted."
                ),
            )
        )
        for attestation_key in rune.attestation_refs:
            attestation = attestations_by_key[attestation_key]
            evidence_status = _rune_evidence_status(attestation, rune.key)
            if evidence_status is None:
                continue
            correspondence_status = {
                "directly-legible": "attested",
                "inferred": "reconstructed",
                "damaged-or-uncertain": "disputed",
            }[evidence_status]
            evidence_label = {
                "directly-legible": "individual rune directly legible",
                "inferred": "individual rune inferred from the recognized 24-rune row",
                "damaged-or-uncertain": "individual rune damaged or uncertain",
            }[evidence_status]
            correspondences.append(
                ImportCorrespondence(
                    key=f"elder-futhark-{rune.row_position:02d}-attestation-{attestation.key}",
                    item=item_ref,
                    type="archaeological_attestation",
                    value=(
                        " · ".join(
                            part
                            for part in (attestation.name, attestation.object_id, attestation.date)
                            if part
                        )
                        + f" · {evidence_label}"
                    ),
                    tradition="elder-futhark",
                    source=attestation.source_refs[0],
                    status=correspondence_status,
                    locator=attestation.object_id,
                    notes=(
                        f"Per-rune epigraphic status: {evidence_label}. "
                        f"Row classification: {attestation.kind}; "
                        f"row completeness: {attestation.row_completeness}. "
                        f"{attestation.notes}"
                    ),
                )
            )
        for poem in sorted(poems_by_item.get(rune.key, []), key=lambda row: row.key):
            interpretations.append(
                ImportInterpretation(
                    key=f"rune-poem-{poem.key}",
                    item=item_ref,
                    source=poem.source,
                    tradition=poem.system,
                    interpretation_type="rune-poem",
                    exact_text=(
                        poem.original_text
                        if poem.latin_tag is None
                        else f"{poem.original_text}\n{poem.latin_tag}"
                    ),
                    locator=poem.locator,
                    sequence=poem.sequence,
                    notes=(
                        f"{poem.mapping_status} mapping to {rune.normalized_label}; "
                        f"{poem.mapping_justification} Exact redistributable English translation "
                        "is not bundled."
                    ),
                )
            )

    bundle = ImportBundle(
        collections=[
            ImportCollection(
                slug=corpus.manifest.slug,
                name=corpus.manifest.name,
                description=corpus.manifest.description,
                system_type=corpus.manifest.system_type,
                supports_reversals=False,
                metadata={
                    "corpus_format_version": corpus.manifest.format_version,
                    "canonical_count": 24,
                    "groups": 3,
                    "casting_method_status": "derived",
                    "blank_rune": False,
                },
                items=items,
            )
        ],
        sources=corpus.sources,
        traditions=corpus.traditions,
        interpretations=interpretations,
        correspondences=correspondences,
    )
    output = corpus.root / "build" / "elder-futhark-import.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    report = validate_corpus(corpus)
    (corpus.root / "build" / "completeness-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or build the Elder Futhark corpus")
    parser.add_argument("command", choices=("validate", "build"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        corpus = load_corpus(args.root)
        result = validate_corpus(corpus)
        if args.command == "build":
            bundle = build_bundle(corpus)
            result["import_items"] = sum(len(row.items) for row in bundle.collections)
            result["import_interpretations"] = len(bundle.interpretations)
            result["import_correspondences"] = len(bundle.correspondences)
    except (OSError, ValidationError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
