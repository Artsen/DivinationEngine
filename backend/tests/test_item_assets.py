from pathlib import Path

from fastapi.testclient import TestClient

ASSET = Path("data/corpus/tarot/rws-1909/images/originals") / "RWS1909 - 00 Fool.jpeg"


def test_rws_item_image_is_served_offline_with_cache_headers(client: TestClient) -> None:
    collection = client.post(
        "/api/v1/collections",
        json={"slug": "rws-1909", "name": "RWS", "system_type": "tarot"},
    ).json()
    item = client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={
            "slug": "the-fool",
            "name": "The Fool",
            "metadata": {
                "image": {
                    "key": "rws1909-image-the-fool",
                    "filename": "RWS1909 - 00 Fool.jpeg",
                }
            },
        },
    ).json()

    response = client.get(f"/api/v1/items/{item['id']}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["etag"].startswith('"')
    assert response.content == ASSET.read_bytes()


def test_item_image_rejects_missing_unknown_and_unattested_paths(
    client: TestClient, collection: dict
) -> None:
    ordinary_item = client.get(f"/api/v1/collections/{collection['id']}/items").json()[0]
    assert client.get(f"/api/v1/items/{ordinary_item['id']}/image").status_code == 404
    assert client.get("/api/v1/items/not-an-item/image").status_code == 404

    rws = client.post(
        "/api/v1/collections",
        json={"slug": "rws-1909", "name": "RWS", "system_type": "tarot"},
    ).json()
    traversal = client.post(
        f"/api/v1/collections/{rws['id']}/items",
        json={
            "slug": "the-fool",
            "name": "The Fool",
            "metadata": {
                "image": {
                    "key": "rws1909-image-the-fool",
                    "filename": "../../../../AGENTS.md",
                }
            },
        },
    ).json()
    response = client.get(f"/api/v1/items/{traversal['id']}/image")
    assert response.status_code == 404
    assert b"Agent invariants" not in response.content
