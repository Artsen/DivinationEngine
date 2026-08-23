import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.services.corpus import RANKS, SUITS, build_bundle, load_corpus, validate_corpus
from app.services.importer import ImportBundle, import_bundle
from tests.conftest import FakeRandom

CORPUS_ROOT = Path("data/corpus/tarot/rws-1909")


def test_rws_corpus_has_canonical_structure_and_verified_images() -> None:
    corpus = load_corpus(CORPUS_ROOT)
    report = validate_corpus(corpus)
    assert report == {
        "cards": 78,
        "majors": 22,
        "minors": 56,
        "wands": 14,
        "cups": 14,
        "swords": 14,
        "pentacles": 14,
        "interpretations": 340,
        "correspondences": 160,
        "images": 78,
        "image_hashes": 78,
    }
    ordered = sorted(corpus.cards, key=lambda card: card.sequence)
    assert [card.sequence for card in ordered] == list(range(78))
    assert ordered[8].name == "Strength" and ordered[8].major_number == 8
    assert ordered[11].name == "Justice" and ordered[11].major_number == 11
    for suit in SUITS:
        assert [card.rank for card in ordered if card.suit == suit] == list(RANKS)


def test_compiler_preserves_exact_text_and_stable_references() -> None:
    corpus = load_corpus(CORPUS_ROOT)
    authoring_text = next(
        row.exact_text
        for card in corpus.cards
        for row in card.interpretations
        if row.key == "waite-pk-the-fool-divinatory-reversed"
    )
    bundle = build_bundle(corpus)
    compiled = ImportBundle.model_validate_json(
        (CORPUS_ROOT / "build" / "rws-import.json").read_text(encoding="utf-8")
    )
    compiled_text = next(
        row.exact_text
        for row in compiled.interpretations
        if row.key == "waite-pk-the-fool-divinatory-reversed"
    )
    assert compiled_text == authoring_text
    assert compiled == bundle
    assert len({row.key for row in bundle.interpretations}) == 340
    assert len({row.key for row in bundle.correspondences}) == 160


def test_real_corpus_import_is_idempotent_and_updates_in_place(
    session_factory: sessionmaker[Session],
) -> None:
    raw = json.loads((CORPUS_ROOT / "build" / "rws-import.json").read_text(encoding="utf-8"))
    bundle = ImportBundle.model_validate(raw)
    with session_factory() as session:
        first = import_bundle(session, bundle)
        first_id = session.scalar(
            select(models.Interpretation.id).where(
                models.Interpretation.key == "waite-pk-the-fool-divinatory-reversed"
            )
        )
        counts = _counts(session)
        second = import_bundle(session, bundle)
        assert first["created"] == sum(counts)
        assert second["created"] == 0
        assert _counts(session) == counts == (1, 78, 3, 2, 340, 160)
        assert (
            session.scalar(
                select(models.Interpretation.id).where(
                    models.Interpretation.key == "waite-pk-the-fool-divinatory-reversed"
                )
            )
            == first_id
        )

        edited = copy.deepcopy(raw)
        target = next(
            row
            for row in edited["interpretations"]
            if row["key"] == "waite-pk-the-fool-divinatory-reversed"
        )
        target["notes"] = "Harmless test-fixture correction."
        import_bundle(session, ImportBundle.model_validate(edited))
        row = session.scalar(
            select(models.Interpretation).where(models.Interpretation.id == first_id)
        )
        assert row is not None and row.notes == "Harmless test-fixture correction."


def test_real_rws_reading_context_is_scoped_reversed_and_provenanced(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    bundle = ImportBundle.model_validate_json(
        (CORPUS_ROOT / "build" / "rws-import.json").read_text(encoding="utf-8")
    )
    with session_factory() as session:
        import_bundle(session, bundle)
    collection = next(
        row for row in client.get("/api/v1/collections").json() if row["slug"] == "rws-1909"
    )
    items = client.get(f"/api/v1/collections/{collection['id']}/items").json()
    assert len(items) == 78
    reading = client.post("/api/v1/readings", json={"title": "RWS verification"}).json()
    client.app.state.random_source = FakeRandom([1, 0])
    first = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1, "reversals_enabled": True},
    ).json()
    assert first["draw_results"][0]["orientation"] == "reversed"
    second = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={
            "collection_id": collection["id"],
            "count": 1,
            "reversals_enabled": True,
            "deck_session_id": first["deck_session_id"],
        },
    ).json()
    assert first["draw_results"][0]["item"]["id"] != second["draw_results"][0]["item"]["id"]

    context = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    first_result = context["casts"][0]["draw_results"][0]
    applicable = first_result["knowledge"]["applicable_interpretations"]
    other = first_result["knowledge"]["other_interpretations"]
    slug = first_result["item"]["slug"]
    reversed_key = f"waite-pk-{slug}-divinatory-reversed"
    upright_key = f"waite-pk-{slug}-divinatory-upright"
    expected_exact_text = next(
        row.exact_text for row in bundle.interpretations if row.key == reversed_key
    )
    assert next(row for row in applicable if row["key"] == reversed_key)["exact_text"] == (
        expected_exact_text
    )
    assert any(row["key"] == upright_key for row in other)
    assert any(row["source_id"] in context["sources"] for row in applicable)
    assert any(row["tradition_id"] in context["traditions"] for row in applicable)
    unrelated_slug = next(item["slug"] for item in items if item["slug"] != slug)
    assert f"waite-pk-{unrelated_slug}-divinatory-upright" not in json.dumps(first_result)


def _counts(session: Session) -> tuple[int, ...]:
    tables = (
        models.Collection,
        models.Item,
        models.Source,
        models.Tradition,
        models.Interpretation,
        models.Correspondence,
    )
    return tuple(session.scalar(select(func.count()).select_from(table)) or 0 for table in tables)
