from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FakeRandom


def test_draw_persists_and_multiple_casts(
    client: TestClient, collection: dict, reading: dict
) -> None:
    draw = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 3, "reversals_enabled": True},
    )
    assert draw.status_code == 201
    original = draw.json()["draw_results"]
    assert len(original) == 3
    assert len({row["item"]["id"] for row in original}) == 3

    iching = client.post(f"/api/v1/readings/{reading['id']}/casts/iching")
    assert iching.status_code == 201
    assert len(iching.json()["iching"]["throws"]) == 6
    assert all(len(row["coins"]) == 3 for row in iching.json()["iching"]["throws"])

    reloaded = client.get(f"/api/v1/readings/{reading['id']}").json()
    assert len(reloaded["casts"]) == 2
    assert reloaded["casts"][0]["draw_results"] == original


def test_draw_too_many_returns_validation_error(
    client: TestClient, collection: dict, reading: dict
) -> None:
    response = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 4},
    )
    assert response.status_code == 422
    assert "cannot exceed" in response.json()["detail"]


def test_fresh_and_continued_deck_sessions(
    client: TestClient, collection: dict, reading: dict
) -> None:
    path = f"/api/v1/readings/{reading['id']}/casts/draw"
    first = client.post(path, json={"collection_id": collection["id"], "count": 1}).json()
    independent = client.post(path, json={"collection_id": collection["id"], "count": 1}).json()
    assert first["deck_session_id"] != independent["deck_session_id"]
    assert first["draw_results"][0]["item"]["id"] == independent["draw_results"][0]["item"]["id"]

    continued = client.post(
        path,
        json={
            "collection_id": collection["id"],
            "count": 2,
            "deck_session_id": first["deck_session_id"],
        },
    )
    assert continued.status_code == 201
    continued_data = continued.json()
    session_items = {
        first["draw_results"][0]["item"]["id"],
        *(row["item"]["id"] for row in continued_data["draw_results"]),
    }
    assert len(session_items) == 3
    assert continued_data["deck_session_id"] == first["deck_session_id"]
    assert continued_data["configuration"]["deck_session_mode"] == "continue"

    exhausted = client.post(
        path,
        json={
            "collection_id": collection["id"],
            "count": 1,
            "deck_session_id": first["deck_session_id"],
        },
    )
    assert exhausted.status_code == 422
    reloaded = client.get(f"/api/v1/readings/{reading['id']}").json()
    assert [cast["deck_session_id"] for cast in reloaded["casts"][:3]] == [
        first["deck_session_id"],
        independent["deck_session_id"],
        first["deck_session_id"],
    ]


def test_deck_session_rejects_wrong_reading_and_collection(
    client: TestClient, collection: dict, reading: dict
) -> None:
    first = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1},
    ).json()
    other_reading = client.post("/api/v1/readings", json={"title": "Other"}).json()
    wrong_reading = client.post(
        f"/api/v1/readings/{other_reading['id']}/casts/draw",
        json={
            "collection_id": collection["id"],
            "count": 1,
            "deck_session_id": first["deck_session_id"],
        },
    )
    assert wrong_reading.status_code == 422
    assert "different reading" in wrong_reading.json()["detail"]

    other_collection = client.post(
        "/api/v1/collections",
        json={"slug": "other-deck", "name": "Other", "system_type": "playing-cards"},
    ).json()
    client.post(
        f"/api/v1/collections/{other_collection['id']}/items",
        json={"slug": "joker", "name": "Joker"},
    )
    wrong_collection = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={
            "collection_id": other_collection["id"],
            "count": 1,
            "deck_session_id": first["deck_session_id"],
        },
    )
    assert wrong_collection.status_code == 422
    assert "different collection" in wrong_collection.json()["detail"]


def test_open_taxonomies_accept_slug_like_future_values(client: TestClient, reading: dict) -> None:
    collection = client.post(
        "/api/v1/collections",
        json={"slug": "future", "name": "Future", "system_type": "playing-cards"},
    )
    assert collection.status_code == 201
    item = client.post(
        f"/api/v1/collections/{collection.json()['id']}/items",
        json={"slug": "marker", "name": "Marker"},
    ).json()
    source = client.post(
        "/api/v1/sources", json={"key": "future-source", "title": "Future Source"}
    ).json()
    interpretation = client.post(
        "/api/v1/interpretations",
        json={
            "key": "future-historical-note",
            "item_id": item["id"],
            "source_id": source["id"],
            "interpretation_type": "historical-note",
            "exact_text": "Fictional fixture only.",
        },
    )
    assert interpretation.status_code == 201
    assert (
        client.post(
            "/api/v1/collections",
            json={"slug": "invalid", "name": "Invalid", "system_type": "Not Valid"},
        ).status_code
        == 422
    )


def test_collection_without_reversals_is_never_reversed(client: TestClient, reading: dict) -> None:
    collection = client.post(
        "/api/v1/collections",
        json={"slug": "runes", "name": "Runes", "system_type": "runes"},
    ).json()
    client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={"slug": "one", "name": "One"},
    )
    client.app.state.random_source = FakeRandom([1])
    cast = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 1, "reversals_enabled": True},
    ).json()
    assert cast["draw_results"][0]["orientation"] == "none"


def test_notes_lifecycle(client: TestClient, reading: dict) -> None:
    created = client.post(f"/api/v1/readings/{reading['id']}/notes", json={"body": "First"})
    assert created.status_code == 201
    note_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/readings/{reading['id']}/notes/{note_id}", json={"body": "Revised"}
    )
    assert updated.json()["body"] == "Revised"
    loaded = client.get(f"/api/v1/readings/{reading['id']}").json()
    assert loaded["notes"][0]["body"] == "Revised"
    deleted = client.delete(f"/api/v1/readings/{reading['id']}/notes/{note_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/readings/{reading['id']}").json()["notes"] == []


def test_spread_and_placements_survive_persistence(
    client: TestClient, collection: dict, reading: dict
) -> None:
    spread_response = client.post(
        "/api/v1/spreads",
        json={
            "slug": "crossing-demo",
            "name": "Crossing Demo",
            "positions": [
                {"label": "Center", "x": 2.5, "y": -1, "rotation": 0, "order": 1},
                {"label": "Crossing", "x": 2.5, "y": -1, "rotation": 90, "order": 2},
            ],
        },
    )
    assert spread_response.status_code == 201
    spread = spread_response.json()
    loaded_spread = client.get(f"/api/v1/spreads/{spread['id']}").json()
    assert loaded_spread["positions"][1]["rotation"] == 90
    assert loaded_spread["positions"][0]["x"] == 2.5

    cast = client.post(
        f"/api/v1/readings/{reading['id']}/casts/draw",
        json={"collection_id": collection["id"], "count": 2},
    ).json()
    result_id = cast["draw_results"][0]["id"]
    placement = client.post(
        f"/api/v1/readings/{reading['id']}/casts/{cast['id']}/placements",
        json={
            "draw_result_id": result_id,
            "spread_id": spread["id"],
            "spread_position_id": spread["positions"][1]["id"],
        },
    )
    assert placement.status_code == 201
    assert placement.json()["rotation"] == 90
    reloaded = client.get(f"/api/v1/readings/{reading['id']}").json()
    assert reloaded["casts"][0]["draw_results"][0]["placement"]["rotation"] == 90


def test_invalid_spread_positions_are_rejected(client: TestClient) -> None:
    duplicate = client.post(
        "/api/v1/spreads",
        json={
            "slug": "bad",
            "name": "Bad",
            "positions": [
                {"label": "A", "x": 0, "y": 0, "order": 1},
                {"label": "B", "x": 1, "y": 0, "order": 1},
            ],
        },
    )
    assert duplicate.status_code == 422
    missing_location = {"draw_result_id": "not-real"}
    response = client.post("/api/v1/readings/x/casts/y/placements", json=missing_location)
    assert response.status_code == 422


def test_common_not_found_and_validation(client: TestClient) -> None:
    assert client.get("/api/v1/readings/not-real").status_code == 404
    assert client.post("/api/v1/readings", json={"title": ""}).status_code == 422
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_app_defaults_to_secure_randomness() -> None:
    app = create_app()
    assert app.state.random_source.__class__.__name__ == "SecureRandomSource"
