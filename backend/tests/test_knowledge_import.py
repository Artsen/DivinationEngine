import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.services.importer import ImportBundle, import_bundle
from tests.conftest import FakeRandom


def test_context_groups_orientation_relevance_and_resolves_provenance(
    client: TestClient, collection: dict, reading: dict
) -> None:
    items = client.get(f"/api/v1/collections/{collection['id']}/items").json()
    alpha, beta = items[0], items[1]
    source = client.post(
        "/api/v1/sources",
        json={
            "key": "fictional-test-source",
            "title": "Fictional Test Source",
            "author": "Test Curator",
            "rights_status": "test_fixture",
        },
    ).json()
    tradition = client.post(
        "/api/v1/traditions",
        json={"slug": "fictional-tradition", "name": "Fictional Tradition"},
    ).json()

    def add_interpretation(key: str, item_id: str, kind: str, text: str) -> None:
        response = client.post(
            "/api/v1/interpretations",
            json={
                "key": key,
                "item_id": item_id,
                "source_id": source["id"],
                "tradition_id": tradition["id"],
                "interpretation_type": kind,
                "exact_text": text,
                "locator": "Exact fixture locator",
            },
        )
        assert response.status_code == 201

    add_interpretation("alpha-upright", alpha["id"], "upright", "Exact upright text.")
    add_interpretation("alpha-reversed", alpha["id"], "reversed", "Exact reversed text.")
    add_interpretation("alpha-symbolism", alpha["id"], "symbolism", "Exact symbol text.")
    add_interpretation("beta-unrelated", beta["id"], "reversed", "Must not appear.")
    correspondence = client.post(
        "/api/v1/correspondences",
        json={
            "key": "alpha-test-correspondence",
            "item_id": alpha["id"],
            "source_id": source["id"],
            "tradition_id": tradition["id"],
            "type": "test-only",
            "value": "alpha",
            "status": "attested",
        },
    )
    assert correspondence.status_code == 201

    client.app.state.random_source = FakeRandom([1])
    draw = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={
            "collection_id": collection["id"],
            "count": 1,
            "reversals_enabled": True,
        },
    )
    assert draw.json()["draw_results"][0]["orientation"] == "reversed"
    context = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    result = context["casts"][0]["draw_results"][0]
    applicable = result["knowledge"]["applicable_interpretations"]
    other = result["knowledge"]["other_interpretations"]
    assert {row["key"] for row in applicable} == {"alpha-reversed", "alpha-symbolism"}
    assert {row["key"] for row in other} == {"alpha-upright"}
    assert (
        next(row for row in applicable if row["key"] == "alpha-reversed")["exact_text"]
        == "Exact reversed text."
    )
    assert "beta-unrelated" not in json.dumps(context)
    assert context["sources"][source["id"]]["title"] == "Fictional Test Source"
    assert context["sources"][source["id"]]["author"] == "Test Curator"
    assert context["traditions"][tradition["id"]]["name"] == "Fictional Tradition"
    assert "generated_interpretation" not in json.dumps(context)


def test_upright_context_relevance(client: TestClient, collection: dict, reading: dict) -> None:
    item = client.get(f"/api/v1/collections/{collection['id']}/items").json()[0]
    source = client.post("/api/v1/sources", json={"key": "source", "title": "Source"}).json()
    for kind in ["upright", "reversed", "divinatory"]:
        client.post(
            "/api/v1/interpretations",
            json={
                "key": f"alpha-{kind}",
                "item_id": item["id"],
                "source_id": source["id"],
                "interpretation_type": kind,
                "exact_text": kind,
            },
        )
    client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1},
    )
    result = client.get(f"/api/v1/readings/{reading['id']}/context").json()["casts"][0][
        "draw_results"
    ][0]
    assert {
        row["interpretation_type"] for row in result["knowledge"]["applicable_interpretations"]
    } == {
        "upright",
        "divinatory",
    }
    assert [row["interpretation_type"] for row in result["knowledge"]["other_interpretations"]] == [
        "reversed"
    ]


def test_importer_is_idempotent_updates_in_place_and_dry_runs(
    session_factory: sessionmaker[Session],
) -> None:
    demo_path = Path("data/examples/demo-import.json")
    raw = json.loads(demo_path.read_text(encoding="utf-8"))
    bundle = ImportBundle.model_validate(raw)
    with session_factory() as session:
        first = import_bundle(session, bundle)
        assert first["created"] == 8
        ids = {
            "collection": session.scalar(select(models.Collection.id)),
            "source": session.scalar(select(models.Source.id)),
            "interpretation": session.scalar(select(models.Interpretation.id)),
            "correspondence": session.scalar(select(models.Correspondence.id)),
        }
        counts = _corpus_counts(session)
        second = import_bundle(session, bundle)
        assert second["created"] == 0
        assert second["updated"] == 8
        assert _corpus_counts(session) == counts
        assert session.scalar(select(models.Collection.id)) == ids["collection"]
        assert session.scalar(select(models.Source.id)) == ids["source"]
        assert session.scalar(select(models.Interpretation.id)) == ids["interpretation"]
        assert session.scalar(select(models.Correspondence.id)) == ids["correspondence"]

        edited = copy.deepcopy(raw)
        edited["interpretations"][0]["exact_text"] = "Corrected exact fixture text."
        import_bundle(session, ImportBundle.model_validate(edited))
        interpretation = session.scalar(select(models.Interpretation))
        assert interpretation is not None
        assert interpretation.id == ids["interpretation"]
        assert interpretation.exact_text == "Corrected exact fixture text."

        dry_run = copy.deepcopy(edited)
        dry_run["interpretations"][0]["exact_text"] = "Never committed."
        result = import_bundle(session, ImportBundle.model_validate(dry_run), dry_run=True)
        assert result["dry_run"] is True
        assert session.scalar(select(models.Interpretation.exact_text)) == (
            "Corrected exact fixture text."
        )


def test_malformed_import_update_rolls_back_every_change(
    session_factory: sessionmaker[Session],
) -> None:
    raw = json.loads(Path("data/examples/demo-import.json").read_text(encoding="utf-8"))
    with session_factory() as session:
        import_bundle(session, ImportBundle.model_validate(raw))
        broken = copy.deepcopy(raw)
        broken["sources"][0]["title"] = "This update must roll back"
        broken["interpretations"][0]["item"] = "missing/item"
        with pytest.raises(ValueError, match="unknown item"):
            import_bundle(session, ImportBundle.model_validate(broken))
        assert session.scalar(select(models.Source.title)) == "Test Deck Demo Manual"
        assert _corpus_counts(session) == (1, 3, 1, 1, 1, 1)


def _corpus_counts(session: Session) -> tuple[int, ...]:
    tables = [
        models.Collection,
        models.Item,
        models.Source,
        models.Tradition,
        models.Interpretation,
        models.Correspondence,
    ]
    return tuple(session.scalar(select(func.count()).select_from(table)) or 0 for table in tables)
