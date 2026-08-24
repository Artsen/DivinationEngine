from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.db import models

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RWS_ASSET_ROOT = REPOSITORY_ROOT / "data" / "corpus" / "tarot" / "rws-1909" / "images"
RWS_ORIGINALS = RWS_ASSET_ROOT / "originals"
RWS_MANIFEST = RWS_ASSET_ROOT / "manifest.json"


@lru_cache
def _rws_images() -> dict[str, dict[str, Any]]:
    rows = json.loads(RWS_MANIFEST.read_text(encoding="utf-8"))
    return {row["key"]: row for row in rows}


def resolve_item_image(item: models.Item) -> tuple[Path, str, str] | None:
    """Resolve a database item only to its attested, committed RWS corpus asset."""
    if item.collection.slug != "rws-1909":
        return None
    image = item.metadata_json.get("image")
    if not isinstance(image, dict):
        return None
    image_key = image.get("key")
    filename = image.get("filename")
    if not isinstance(image_key, str) or not isinstance(filename, str):
        return None
    manifest_row = _rws_images().get(image_key)
    if (
        manifest_row is None
        or manifest_row.get("card") != f"rws-1909/{item.slug}"
        or manifest_row.get("filename") != filename
    ):
        return None
    originals = RWS_ORIGINALS.resolve()
    candidate = (originals / filename).resolve()
    if candidate.parent != originals or not candidate.is_file():
        return None
    media_type = manifest_row.get("format")
    sha256 = manifest_row.get("sha256")
    if not isinstance(media_type, str) or not isinstance(sha256, str):
        return None
    return candidate, media_type, sha256
