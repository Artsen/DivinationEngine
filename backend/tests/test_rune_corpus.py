import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.services.importer import ImportBundle, import_bundle
from app.services.rune_corpus import build_bundle, load_corpus, validate_corpus

ROOT = Path("data/corpus/runes/elder-futhark")


def test_corpus_has_exact_historical_layers_and_counts() -> None:
    corpus = load_corpus(ROOT)
    report = validate_corpus(corpus)
    assert report == {
        "runes": 24,
        "aett_groups": 3,
        "reconstructed_names": 24,
        "caution_records": 4,
        "old_english_stanzas": 29,
        "norwegian_stanzas": 16,
        "icelandic_stanzas": 16,
        "stanzas": 61,
        "original_language_bodies": 61,
        "english_exact_texts": 0,
        "english_omitted": 61,
        "editorial_translations": 61,
        "machine_assisted_editorial_translations": 61,
        "editorial_translation_missing": 0,
        "editorial_translation_caution_notes": 30,
        "poem_mappings": 56,
        "direct_mappings": 53,
        "cautious_mappings": 3,
        "unmapped_expansions": 5,
        "attestations": 5,
        "complete_row_witnesses": 1,
        "damaged_row_witnesses": 2,
        "legible_rune_links": 65,
        "inferred_rune_links": 1,
        "uncertain_rune_links": 6,
    }
    assert [row.row_position for row in corpus.runes] == list(range(1, 25))
    assert all(row.reconstruction_status == "reconstructed" for row in corpus.runes)
    assert {
        row.normalized_name for row in corpus.poems if row.mapping_status == "not-applicable"
    } == {"Ac", "Æsc", "Yr", "Iar", "Ear"}
    assert all(row.english_exact_text is None for row in corpus.poems)


def test_damaged_row_witnesses_preserve_per_rune_epigraphic_status() -> None:
    corpus = load_corpus(ROOT)
    attestations = {row.key: row for row in corpus.attestations}
    kylver = attestations["kylver-g88"]
    vadstena = attestations["vadstena-bracteate"]
    grumpan = attestations["grumpan-bracteate"]

    assert kylver.kind == "complete-row"
    assert len(kylver.legible_rune_items) == 24
    assert not kylver.inferred_rune_items
    assert not kylver.uncertain_rune_items
    assert vadstena.kind == "full-row-with-damage"
    assert set(vadstena.uncertain_rune_items) == {
        "runes/elder-futhark/14",
        "runes/elder-futhark/23",
    }
    assert grumpan.inferred_rune_items == ["runes/elder-futhark/16"]
    assert set(grumpan.uncertain_rune_items) == {
        "runes/elder-futhark/14",
        "runes/elder-futhark/15",
        "runes/elder-futhark/22",
        "runes/elder-futhark/24",
    }

    bundle = build_bundle(corpus)
    items = {row.slug: row for row in bundle.collections[0].items}
    perthro_evidence = items["perthro"].metadata["attestation_evidence"]
    assert "attestation_refs" not in items["perthro"].metadata
    assert {(row["key"], row["rune_evidence_status"]) for row in perthro_evidence} == {
        ("kylver-g88", "directly-legible"),
        ("vadstena-bracteate", "damaged-or-uncertain"),
        ("grumpan-bracteate", "damaged-or-uncertain"),
    }
    correspondence_by_key = {row.key: row for row in bundle.correspondences}
    assert (
        correspondence_by_key["elder-futhark-14-attestation-grumpan-bracteate"].status == "disputed"
    )
    assert (
        correspondence_by_key["elder-futhark-16-attestation-grumpan-bracteate"].status
        == "reconstructed"
    )
    assert (
        correspondence_by_key["elder-futhark-01-attestation-grumpan-bracteate"].status == "attested"
    )


def test_source_checked_identity_and_difficult_mapping_fixtures() -> None:
    corpus = load_corpus(ROOT)
    by_slug = {row.slug: row for row in corpus.runes}
    for slug in ("fehu", "kenaz", "eihwaz", "perthro", "algiz", "laguz", "othala"):
        rune = by_slug[slug]
        assert rune.glyph
        assert rune.transliteration
        assert "ut-lrc-old-norse-runes" in rune.source_refs
    assert by_slug["fehu"].proto_germanic_name == "fehu"
    assert by_slug["fehu"].lexical_reconstruction == "cattle, possessions"
    assert by_slug["algiz"].name_evidence_status == "disputed"
    algiz_poems = [row for row in corpus.poems if row.elder_futhark_item == by_slug["algiz"].key]
    assert len(algiz_poems) == 3
    assert {row.mapping_status for row in algiz_poems} == {"likely-related"}
    assert {row.system for row in algiz_poems} == {"anglo-saxon-futhorc", "younger-futhark"}
    assert "modern" not in json.dumps([row.model_dump() for row in corpus.runes]).lower()


def test_build_is_deterministic_and_uses_generic_collection_engine() -> None:
    first = build_bundle(load_corpus(ROOT)).model_dump_json(indent=2)
    second = build_bundle(load_corpus(ROOT)).model_dump_json(indent=2)
    assert first == second
    bundle = ImportBundle.model_validate_json(first)
    collection = bundle.collections[0]
    assert collection.system_type == "runes"
    assert collection.supports_reversals is False
    assert len(collection.items) == 24
    assert bundle.interpretations == []
    assert len(bundle.rune_poems) == 61
    assert all(row.translation_type == "project-editorial" for row in bundle.rune_poems)
    assert all(row.translation_status == "derived" for row in bundle.rune_poems)
    assert all(row.machine_assisted is True for row in bundle.rune_poems)
    assert all(len(row.translation_sources) >= 2 for row in bundle.rune_poems)


def test_editorial_poems_preserve_originals_and_cautious_mappings() -> None:
    corpus = load_corpus(ROOT)
    bundle = build_bundle(corpus)
    poem_by_key = {row.key: row for row in bundle.rune_poems}
    assert {key: poem_by_key[key].original_text for key in poem_by_key} == {
        row.key: row.original_text for row in corpus.poems
    }
    assert sum(row.editorial_latin_gloss is not None for row in bundle.rune_poems) == 16
    assert all(
        "dickins" not in " ".join([row.translator, *row.translation_sources]).lower()
        for row in bundle.rune_poems
    )

    fehu = [row for row in bundle.rune_poems if row.item == "elder-futhark/fehu"]
    assert len(fehu) == 3
    assert {row.poem for row in fehu} == {"old-english", "norwegian", "icelandic"}
    assert all(row.mapping_status == "direct" for row in fehu)
    assert "bosworth-toller-1898" in poem_by_key["old-english-01-feoh"].translation_sources

    algiz = [row for row in bundle.rune_poems if row.item == "elder-futhark/algiz"]
    assert len(algiz) == 3
    assert all(row.mapping_status == "likely-related" for row in algiz)
    expansions = [row for row in bundle.rune_poems if row.mapping_status == "not-applicable"]
    assert len(expansions) == 5
    assert all(row.item is None for row in expansions)


def test_validator_rejects_missing_or_misattributed_editorial_translations() -> None:
    corpus = load_corpus(ROOT)
    with pytest.raises(ValueError, match="missing editorial translations"):
        validate_corpus(
            corpus.model_copy(update={"editorial_translations": corpus.editorial_translations[:-1]})
        )

    first = corpus.editorial_translations[0]
    misattributed = first.model_copy(
        update={"translator": "Bruce Dickins", "source_refs": [*first.source_refs, "dickins-1915"]}
    )
    with pytest.raises(ValueError, match="cannot claim Dickins provenance"):
        validate_corpus(
            corpus.model_copy(
                update={
                    "editorial_translations": [
                        misattributed,
                        *corpus.editorial_translations[1:],
                    ]
                }
            )
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda corpus: corpus.model_copy(update={"runes": corpus.runes + [corpus.runes[0]]}),
            "expected 24",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={
                    "runes": [
                        corpus.runes[0].model_copy(update={"row_position": 2}),
                        *corpus.runes[1:],
                    ]
                }
            ),
            "positions must be exactly",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={
                    "runes": [
                        corpus.runes[0].model_copy(update={"source_refs": ["missing"]}),
                        *corpus.runes[1:],
                    ]
                }
            ),
            "unknown source",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={
                    "poems": [
                        corpus.poems[0].model_copy(update={"original_text": ""}),
                        *corpus.poems[1:],
                    ]
                }
            ),
            "missing original-language",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={"manifest": corpus.manifest.model_copy(update={"supports_reversals": True})}
            ),
            "cannot support reversals",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={
                    "runes": [
                        corpus.runes[0].model_copy(update={"normalized_label": "Blank rune"}),
                        *corpus.runes[1:],
                    ]
                }
            ),
            "blank rune",
        ),
        (
            lambda corpus: corpus.model_copy(
                update={
                    "attestations": [
                        corpus.attestations[0].model_copy(
                            update={"uncertain_rune_items": ["runes/elder-futhark/01"]}
                        ),
                        *corpus.attestations[1:],
                    ]
                }
            ),
            "statuses overlap",
        ),
    ],
)
def test_validator_rejects_malformed_corpus(mutation, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_corpus(mutation(load_corpus(ROOT)))


def test_import_is_idempotent_and_rolls_back_bad_reference(
    session_factory: sessionmaker[Session],
) -> None:
    raw = json.loads((ROOT / "build" / "elder-futhark-import.json").read_text(encoding="utf-8"))
    with session_factory() as session:
        first = import_bundle(session, ImportBundle.model_validate(raw))
        ids = session.scalars(
            select(models.Item.id)
            .join(models.Collection)
            .where(models.Collection.slug == "elder-futhark")
        ).all()
        second = import_bundle(session, ImportBundle.model_validate(raw))
        assert first["created"] > 0
        assert second["created"] == 0
        assert len(ids) == 24
        assert (
            session.scalars(
                select(models.Item.id)
                .join(models.Collection)
                .where(models.Collection.slug == "elder-futhark")
            ).all()
            == ids
        )

        broken = copy.deepcopy(raw)
        broken["sources"][0]["title"] = "must roll back"
        broken["rune_poems"][0]["source"] = "missing-source"
        with pytest.raises(ValueError, match="unknown source"):
            import_bundle(session, ImportBundle.model_validate(broken))
        assert (
            session.scalar(
                select(models.Source.title).where(models.Source.key == raw["sources"][0]["key"])
            )
            != "must roll back"
        )
        assert session.scalar(select(func.count()).select_from(models.Item)) == 24


def test_rune_draw_context_sessions_exhaustion_and_persistence(
    client: TestClient, session_factory: sessionmaker[Session], reading: dict
) -> None:
    bundle = ImportBundle.model_validate_json(
        (ROOT / "build" / "elder-futhark-import.json").read_text(encoding="utf-8")
    )
    with session_factory() as session:
        import_bundle(session, bundle)
    collection = next(
        row for row in client.get("/api/v1/collections").json() if row["slug"] == "elder-futhark"
    )
    path = f"/api/v1/readings/{reading['id']}/casts/draw"
    first = client.post(
        path, json={"collection_id": collection["id"], "count": 3, "reversals_enabled": True}
    )
    assert first.status_code == 201
    first_data = first.json()
    assert [row["draw_order"] for row in first_data["draw_results"]] == [1, 2, 3]
    assert len({row["item"]["id"] for row in first_data["draw_results"]}) == 3
    assert {row["orientation"] for row in first_data["draw_results"]} == {"none"}

    continued = client.post(
        path,
        json={
            "collection_id": collection["id"],
            "count": 21,
            "deck_session_id": first_data["deck_session_id"],
        },
    )
    assert continued.status_code == 201
    assert (
        client.post(
            path,
            json={
                "collection_id": collection["id"],
                "count": 1,
                "deck_session_id": first_data["deck_session_id"],
            },
        ).status_code
        == 422
    )
    independent = client.post(path, json={"collection_id": collection["id"], "count": 1}).json()
    assert (
        independent["draw_results"][0]["item"]["id"] == first_data["draw_results"][0]["item"]["id"]
    )

    before = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    after = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    assert before["casts"] == after["casts"]
    fehu = next(
        result
        for cast in before["casts"]
        for result in cast["draw_results"]
        if result["item"]["slug"] == "fehu"
    )
    assert fehu["item"]["symbol"] == "ᚠ"
    assert fehu["item"]["metadata"]["reconstruction_status"] == "reconstructed"
    poems = fehu["knowledge"]["rune_poems"]
    assert len(poems) == 3
    assert {before["traditions"][row["tradition_id"]]["name"] for row in poems} == {
        "Anglo-Saxon Futhorc",
        "Younger Futhark",
    }
    assert all(row["source_id"] in before["sources"] for row in poems)
    assert all(row["translation_type"] == "project-editorial" for row in poems)
    assert all(row["translation_status"] == "derived" for row in poems)
    assert all(row["machine_assisted"] is True for row in poems)
    assert all(
        source_id in before["sources"]
        for row in poems
        for source_id in row["translation_source_ids"]
    )
    assert fehu["knowledge"]["other_interpretations"] == []
    assert "attestation_refs" not in fehu["item"]["metadata"]
    assert all(
        "rune_evidence_status" in row for row in fehu["item"]["metadata"]["attestation_evidence"]
    )

    results_by_slug = {
        result["item"]["slug"]: result
        for cast in before["casts"]
        for result in cast["draw_results"]
    }
    perthro_grumpan = next(
        row
        for row in results_by_slug["perthro"]["knowledge"]["correspondences"]
        if row["key"] == "elder-futhark-14-attestation-grumpan-bracteate"
    )
    sowilo_grumpan = next(
        row
        for row in results_by_slug["sowilo"]["knowledge"]["correspondences"]
        if row["key"] == "elder-futhark-16-attestation-grumpan-bracteate"
    )
    assert perthro_grumpan["status"] == "disputed"
    assert "damaged or uncertain" in perthro_grumpan["notes"]
    assert sowilo_grumpan["status"] == "reconstructed"
    assert "inferred from the recognized 24-rune row" in sowilo_grumpan["notes"]
    assert perthro_grumpan["source_id"] in before["sources"]
    assert sowilo_grumpan["source_id"] in before["sources"]
    status = client.get("/api/v1/corpus-status").json()
    assert status["runes_ready"] is True
    assert status["elder_futhark_item_count"] == 24
    assert status["rune_poem_count"] == 61
    all_poems = client.get("/api/v1/rune-poems")
    assert all_poems.status_code == 200
    assert len(all_poems.json()) == 61
    assert sum(row["item_id"] is None for row in all_poems.json()) == 5
