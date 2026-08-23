import json
from collections import Counter
from itertools import product
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.domain.iching import cast_yarrow_stalk
from app.services.iching_corpus import PATTERNS, validate
from app.services.importer import ImportBundle, import_bundle
from tests.conftest import FakeRandom

CORPUS_ROOT = Path("data/corpus/iching/legge-ctext")


def _bundle() -> ImportBundle:
    return ImportBundle.model_validate_json(
        (CORPUS_ROOT / "build" / "iching-import.json").read_text(encoding="utf-8")
    )


def test_corpus_has_complete_bilingual_layers_and_no_collection() -> None:
    result = validate(CORPUS_ROOT)
    assert result == {
        "trigrams": 8,
        "hexagrams": 64,
        "ordinary_lines": 384,
        "texts": 2022,
        "relationships": 576,
        "single_line_transformations": 384,
        "methods": 2,
    }
    bundle = _bundle()
    assert bundle.collections == []
    counts = Counter((row.layer, row.language, row.unit_type) for row in bundle.iching_texts)
    for layer, unit, count in (
        ("zhouyi-core", "gua-ci", 64),
        ("zhouyi-core", "yao-ci", 384),
        ("tuan-zhuan", "tuan", 64),
        ("xiang-zhuan-great-image", "great-image", 64),
        ("xiang-zhuan-line-image", "line-image", 384),
    ):
        assert counts[layer, "zh-Hant", unit] == count
        assert counts[layer, "en", unit] == count
    assert {row.layer for row in bundle.iching_texts} >= {
        "wenyan-zhuan",
        "xici-zhuan",
        "shuo-gua-zhuan",
        "xu-gua-zhuan",
        "za-gua-zhuan",
        "legge-commentary",
        "yarrow-divination",
        "three-coin-divination",
    }
    corrections = json.loads((CORPUS_ROOT / "corrections.json").read_text(encoding="utf-8"))
    assert corrections["corrections"] == []


def test_patterns_relationships_and_special_use_invariants() -> None:
    bundle = _bundle()
    assert [row.binary_pattern for row in bundle.hexagrams] == PATTERNS
    assert bundle.hexagrams[0].glyph == "䷀"
    assert bundle.hexagrams[1].glyph == "䷁"
    assert bundle.hexagrams[62].binary_pattern == "101010"
    assert bundle.hexagrams[63].binary_pattern == "010101"
    assert all(
        line.polarity
        == ("yang" if PATTERNS[int(line.hexagram[-2:]) - 1][line.position - 1] == "1" else "yin")
        for line in bundle.hexagram_lines
    )
    relation_counts = Counter(row.relationship_type for row in bundle.iching_relationships)
    assert relation_counts == {
        "single-line-change": 384,
        "complement": 64,
        "inversion": 64,
        "nuclear": 64,
    }
    special = [row for row in bundle.iching_texts if row.unit_type == "special-use"]
    assert len(special) == 4
    assert {row.hexagram for row in special} == {"hexagram-01", "hexagram-02"}
    assert all(row.line_position is None for row in special)


def test_import_is_idempotent_and_persists_all_algorithmic_entities(
    session_factory: sessionmaker[Session],
) -> None:
    bundle = _bundle()
    with session_factory() as session:
        first = import_bundle(session, bundle)
        second = import_bundle(session, bundle)
        assert first["created"] > 0
        assert second["created"] == 0
        assert second["updated"] > 0
        assert session.scalar(select(func.count()).select_from(models.Trigram)) == 8
        assert session.scalar(select(func.count()).select_from(models.Hexagram)) == 64
        assert session.scalar(select(func.count()).select_from(models.HexagramLine)) == 384
        assert session.scalar(select(func.count()).select_from(models.IChingText)) == 2022
        assert session.scalar(select(func.count()).select_from(models.IChingRelationship)) == 576
        assert session.scalar(select(func.count()).select_from(models.IChingMethod)) == 2


def test_yarrow_cast_records_all_eighteen_real_manipulations() -> None:
    result = cast_yarrow_stalk(FakeRandom(numbers=list(range(100)), bits=[0, 1] * 20))
    assert len(result.throws) == 6
    assert sum(len(throw.manipulations) for throw in result.throws) == 18  # type: ignore[union-attr]
    for throw in result.throws:
        assert throw.value in {6, 7, 8, 9}
        for manipulation in throw.manipulations:  # type: ignore[union-attr]
            assert manipulation.remaining_stalks % 4 == 0
            assert manipulation.removed_total in ({5, 9} if manipulation.operation == 1 else {4, 8})


def test_yarrow_remainder_classes_produce_exact_reconstructed_distribution() -> None:
    counts: Counter[int] = Counter()
    for classes in product(range(4), repeat=3):
        line_numbers = [value for pair in zip(classes, (0, 0, 0), strict=True) for value in pair]
        result = cast_yarrow_stalk(FakeRandom(numbers=line_numbers * 6))
        counts[result.throws[0].value] += 1
    assert counts == {6: 4, 7: 20, 8: 28, 9: 12}


def test_context_returns_exact_changing_line_texts_and_provenance(
    client: TestClient,
    session_factory: sessionmaker[Session],
    reading: dict,
) -> None:
    with session_factory() as session:
        import_bundle(session, _bundle())
    # [7, 8, 6, 9, 7, 8], bottom-to-top.
    client.app.state.random_source = FakeRandom(
        [0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1]
    )
    cast = client.post(
        f"/api/v1/readings/{reading['id']}/casts/iching", json={"method": "three-coin"}
    )
    assert cast.status_code == 201
    assert cast.json()["iching"]["primary_pattern"] == "100110"
    assert cast.json()["iching"]["relating_pattern"] == "101010"
    assert cast.json()["iching"]["changing_lines"] == [3, 4]

    context = client.get(f"/api/v1/readings/{reading['id']}/context")
    assert context.status_code == 200
    knowledge = context.json()["casts"][0]["iching"]["knowledge"]
    assert knowledge["primary"]["key"] == "hexagram-17"
    assert knowledge["relating"]["key"] == "hexagram-63"
    selected = knowledge["primary"]["texts"]
    changing = [row for row in selected if row["line_position"] is not None]
    assert {row["line_position"] for row in changing} == {3, 4}
    assert {row["language"] for row in changing} == {"en", "zh-Hant"}
    assert all(row["exact_text"] and row["locator"] and row["source_id"] for row in selected)


def test_yarrow_api_persists_method_and_procedure(client: TestClient, reading: dict) -> None:
    response = client.post(
        f"/api/v1/readings/{reading['id']}/casts/iching", json={"method": "yarrow-stalk"}
    )
    assert response.status_code == 201
    data = response.json()["iching"]
    assert data["method"] == "yarrow-stalk"
    assert all(row["coins"] is None for row in data["throws"])
    assert all(len(row["procedure"]["manipulations"]) == 3 for row in data["throws"])
