from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.services.spreads import BUILTIN_SPREADS, install_builtin_spreads


def test_builtin_spreads_are_small_classified_and_idempotent(
    session_factory: sessionmaker[Session], client: TestClient
) -> None:
    with session_factory() as session:
        first = install_builtin_spreads(session)
        second = install_builtin_spreads(session)
        assert first == {"created": 4, "updated": 0}
        assert second == {"created": 0, "updated": 4}
        assert session.scalar(select(func.count(models.SpreadDefinition.id))) == 4

    spreads = client.get("/api/v1/spreads").json()
    assert {spread["slug"] for spread in spreads} == {
        definition.key for definition in BUILTIN_SPREADS
    }
    assert all(spread["origin"] == "builtin" for spread in spreads)
    assert all(spread["classification"] == "modern-editorial-layout" for spread in spreads)
    assert all(spread["source_label"] for spread in spreads)


def test_custom_spread_creation_generates_stable_keys_and_normalized_coordinates(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/spreads",
        json={
            "name": "Career Decision",
            "system_types": ["tarot", "runes"],
            "positions": [
                {"label": "Current situation", "order": 1},
                {"label": "Opportunity", "order": 2},
                {"label": "Risk", "order": 3},
            ],
        },
    )
    assert response.status_code == 201
    spread = response.json()
    assert spread["slug"].startswith("custom-")
    assert spread["origin"] == "custom"
    assert spread["classification"] == "custom-user-layout"
    assert [position["key"] for position in spread["positions"]] == [
        "current-situation",
        "opportunity",
        "risk",
    ]
    assert all(0 <= position["x"] <= 1 for position in spread["positions"])
    ids_by_key = {position["key"]: position["id"] for position in spread["positions"]}
    reordered = client.patch(
        f"/api/v1/spreads/{spread['id']}",
        json={
            "positions": [
                {"key": "risk", "label": "Risk", "order": 1},
                {"key": "opportunity", "label": "Opportunity", "order": 2},
                {"key": "current-situation", "label": "Current situation", "order": 3},
            ]
        },
    ).json()
    assert [position["key"] for position in reordered["positions"]] == [
        "risk",
        "opportunity",
        "current-situation",
    ]
    assert {position["key"]: position["id"] for position in reordered["positions"]} == ids_by_key


def test_duplicate_position_keys_and_sequences_are_rejected(client: TestClient) -> None:
    base = {
        "name": "Invalid",
        "system_types": ["tarot"],
        "positions": [
            {"key": "same", "label": "A", "order": 1},
            {"key": "same", "label": "B", "order": 2},
        ],
    }
    assert client.post("/api/v1/spreads", json=base).status_code == 422
    base["positions"][1] = {"key": "other", "label": "B", "order": 1}
    assert client.post("/api/v1/spreads", json=base).status_code == 422
    base["positions"] = [{"label": "   ", "order": 1}]
    assert client.post("/api/v1/spreads", json=base).status_code == 422


def test_database_rejects_duplicate_position_key(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        spread = models.SpreadDefinition(
            slug="db-check",
            name="DB check",
            origin="custom",
            classification="custom-user-layout",
            system_types=["tarot"],
        )
        spread.positions = [
            models.SpreadPosition(key="same", label="A", x=0.2, y=0.5, order=1),
            models.SpreadPosition(key="same", label="B", x=0.8, y=0.5, order=2),
        ]
        session.add(spread)
        try:
            session.commit()
            raise AssertionError("duplicate key should fail")
        except IntegrityError:
            session.rollback()


def test_cast_auto_assigns_and_snapshots_custom_spread(
    client: TestClient, collection: dict, reading: dict
) -> None:
    spread = client.post(
        "/api/v1/spreads",
        json={
            "name": "Decision",
            "system_types": ["oracle"],
            "positions": [
                {
                    "key": "situation",
                    "label": "Situation",
                    "description": "Current facts.",
                    "order": 1,
                },
                {
                    "key": "advice",
                    "label": "Advice",
                    "description": "A response to consider.",
                    "order": 2,
                },
            ],
        },
    ).json()
    path = f"/api/v1/readings/{reading['id']}/casts/draw"
    mismatch = client.post(
        path,
        json={"collection_id": collection["id"], "count": 1, "spread_id": spread["id"]},
    )
    assert mismatch.status_code == 422

    cast_response = client.post(
        path,
        json={"collection_id": collection["id"], "count": 2, "spread_id": spread["id"]},
    )
    assert cast_response.status_code == 201
    cast = cast_response.json()
    assert cast["spread"] == {
        "id": spread["id"],
        "key": spread["slug"],
        "name": "Decision",
        "classification": "custom-user-layout",
    }
    assert [row["placement"]["position_key"] for row in cast["draw_results"]] == [
        "situation",
        "advice",
    ]

    updated = client.patch(
        f"/api/v1/spreads/{spread['id']}",
        json={
            "name": "Renamed Decision",
            "positions": [
                {"key": "main-risk", "label": "Main Risk", "description": "Changed.", "order": 1},
                {
                    "key": "next-step",
                    "label": "Next Step",
                    "description": "Changed too.",
                    "order": 2,
                },
            ],
        },
    )
    assert updated.status_code == 200
    context = client.get(f"/api/v1/readings/{reading['id']}/context").json()
    historical = context["casts"][0]
    assert historical["spread"]["name"] == "Decision"
    assert [row["placement"]["position_label"] for row in historical["draw_results"]] == [
        "Situation",
        "Advice",
    ]
    assert historical["draw_results"][0]["placement"]["position_description"] == "Current facts."


def test_unstructured_legacy_draw_remains_unplaced(
    client: TestClient, collection: dict, reading: dict
) -> None:
    cast = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1},
    ).json()
    assert cast["spread"] is None
    assert cast["draw_results"][0]["placement"] is None


def test_place_later_enforces_applicability_and_normalized_coordinates(
    client: TestClient, collection: dict, reading: dict
) -> None:
    cast = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1},
    ).json()
    spread = client.post(
        "/api/v1/spreads",
        json={
            "name": "Tarot only",
            "system_types": ["tarot"],
            "positions": [{"label": "Focus", "order": 1}],
        },
    ).json()
    endpoint = f"/api/v1/readings/{reading['id']}/casts/{cast['id']}/placements"
    incompatible = client.post(
        endpoint,
        json={
            "draw_result_id": cast["draw_results"][0]["id"],
            "spread_id": spread["id"],
            "spread_position_id": spread["positions"][0]["id"],
        },
    )
    assert incompatible.status_code == 422
    invalid_coordinate = client.post(
        endpoint,
        json={"draw_result_id": cast["draw_results"][0]["id"], "x": 2, "y": 0.5},
    )
    assert invalid_coordinate.status_code == 422
