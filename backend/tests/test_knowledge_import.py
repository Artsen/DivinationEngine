import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.services.importer import ImportBundle, import_bundle


def test_knowledge_provenance_and_facts_only_context(
    client: TestClient, collection: dict, reading: dict
) -> None:
    item = client.get(f"/api/v1/collections/{collection['id']}/items").json()[0]
    source = client.post(
        "/api/v1/sources",
        json={"title": "Fictional Test Source", "rights_status": "test_fixture"},
    ).json()
    interpretation = client.post(
        "/api/v1/interpretations",
        json={
            "item_id": item["id"],
            "source_id": source["id"],
            "interpretation_type": "description",
            "exact_text": "A deliberately fictional test statement.",
            "locator": "p. 1",
        },
    )
    assert interpretation.status_code == 201
    assert interpretation.json()["source_id"] == source["id"]
    correspondence = client.post(
        "/api/v1/correspondences",
        json={
            "item_id": item["id"],
            "source_id": source["id"],
            "type": "test-only",
            "value": "alpha",
            "status": "attested",
        },
    )
    assert correspondence.status_code == 201

    client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1},
    )
    context = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    assert context["knowledge"]["interpretations"][0]["source_id"] == source["id"]
    assert context["knowledge"]["correspondences"][0]["source_id"] == source["id"]
    assert "generated" in context["knowledge"]["notice"].lower()
    assert "interpretation" not in context or "generated_interpretation" not in context


def test_importer_validates_references_and_is_transactional(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    demo_path = Path("data/examples/demo-import.json")
    bundle = ImportBundle.model_validate_json(demo_path.read_text(encoding="utf-8"))
    with session_factory() as session:
        result = import_bundle(session, bundle)
        assert result == {
            "collections": 1,
            "items": 3,
            "sources": 1,
            "traditions": 1,
            "interpretations": 1,
            "correspondences": 1,
        }
        interpretation = session.scalar(select(models.Interpretation))
        assert interpretation is not None
        assert interpretation.source_id == session.scalar(select(models.Source.id))

    broken_data = json.loads(demo_path.read_text(encoding="utf-8"))
    broken_data["collections"][0]["slug"] = "another-deck"
    broken_data["traditions"][0]["slug"] = "another-demo"
    broken_data["interpretations"][0]["tradition"] = "another-demo"
    broken_data["interpretations"][0]["item"] = "missing/item"
    broken = ImportBundle.model_validate(broken_data)
    with session_factory() as session:
        before = session.scalar(select(func.count()).select_from(models.Collection))
        with pytest.raises(ValueError, match="unknown item"):
            import_bundle(session, broken)
        after = session.scalar(select(func.count()).select_from(models.Collection))
        assert after == before
