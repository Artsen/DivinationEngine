import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.schemas.contracts import (
    CollectionCreate,
    CorrespondenceStatus,
    InterpretationType,
    ItemCreate,
    SourceCreate,
    TraditionCreate,
)


class ImportCollection(CollectionCreate):
    items: list[ItemCreate] = Field(default_factory=list)


class ImportSource(SourceCreate):
    key: str = Field(min_length=1, pattern=r"^[a-z0-9_-]+$")


class ImportInterpretation(BaseModel):
    item: str = Field(description="collection-slug/item-slug")
    source: str = Field(description="source key from this document")
    tradition: str | None = Field(default=None, description="tradition slug")
    interpretation_type: InterpretationType
    exact_text: str = Field(min_length=1)
    locator: str | None = None
    sequence: int | None = None
    notes: str | None = None


class ImportCorrespondence(BaseModel):
    item: str
    type: str = Field(min_length=1)
    value: str | None = None
    tradition: str | None = None
    source: str
    status: CorrespondenceStatus
    locator: str | None = None
    notes: str | None = None


class ImportBundle(BaseModel):
    format_version: Literal["1"] = "1"
    collections: list[ImportCollection] = Field(default_factory=list)
    sources: list[ImportSource] = Field(default_factory=list)
    traditions: list[TraditionCreate] = Field(default_factory=list)
    interpretations: list[ImportInterpretation] = Field(default_factory=list)
    correspondences: list[ImportCorrespondence] = Field(default_factory=list)


def import_bundle(session: Session, bundle: ImportBundle) -> dict[str, int]:
    if bundle.format_version != "1":
        raise ValueError("unsupported format_version")
    source_ids: dict[str, str] = {}
    tradition_ids: dict[str, str] = {}
    item_ids: dict[str, str] = {}
    try:
        for tradition_data in bundle.traditions:
            if tradition_data.slug in tradition_ids:
                raise ValueError(f"duplicate tradition key: {tradition_data.slug}")
            tradition_row = models.Tradition(**tradition_data.model_dump())
            session.add(tradition_row)
            session.flush()
            tradition_ids[tradition_data.slug] = tradition_row.id
        for source_data in bundle.sources:
            if source_data.key in source_ids:
                raise ValueError(f"duplicate source key: {source_data.key}")
            values = source_data.model_dump(exclude={"key"})
            values["source_url"] = str(source_data.source_url) if source_data.source_url else None
            source_row = models.Source(**values)
            session.add(source_row)
            session.flush()
            source_ids[source_data.key] = source_row.id
        for collection_data in bundle.collections:
            collection_row = models.Collection(
                **collection_data.model_dump(exclude={"items", "metadata"}),
                metadata_json=collection_data.metadata,
            )
            session.add(collection_row)
            session.flush()
            for item_data in collection_data.items:
                key = f"{collection_data.slug}/{item_data.slug}"
                if key in item_ids:
                    raise ValueError(f"duplicate item reference: {key}")
                item = models.Item(
                    collection_id=collection_row.id,
                    **item_data.model_dump(exclude={"metadata"}),
                    metadata_json=item_data.metadata,
                )
                session.add(item)
                session.flush()
                item_ids[key] = item.id
        for interpretation_data in bundle.interpretations:
            session.add(
                models.Interpretation(
                    item_id=_ref(item_ids, interpretation_data.item, "item"),
                    source_id=_ref(source_ids, interpretation_data.source, "source"),
                    tradition_id=_optional_ref(
                        tradition_ids, interpretation_data.tradition, "tradition"
                    ),
                    **interpretation_data.model_dump(exclude={"item", "source", "tradition"}),
                )
            )
        for correspondence_data in bundle.correspondences:
            session.add(
                models.Correspondence(
                    item_id=_ref(item_ids, correspondence_data.item, "item"),
                    source_id=_ref(source_ids, correspondence_data.source, "source"),
                    tradition_id=_optional_ref(
                        tradition_ids, correspondence_data.tradition, "tradition"
                    ),
                    **correspondence_data.model_dump(exclude={"item", "source", "tradition"}),
                )
            )
        session.commit()
    except (IntegrityError, ValueError):
        session.rollback()
        raise
    return {
        "collections": len(bundle.collections),
        "items": len(item_ids),
        "sources": len(bundle.sources),
        "traditions": len(bundle.traditions),
        "interpretations": len(bundle.interpretations),
        "correspondences": len(bundle.correspondences),
    }


def _ref(mapping: dict[str, str], key: str, kind: str) -> str:
    try:
        return mapping[key]
    except KeyError as exc:
        raise ValueError(f"unknown {kind} reference: {key}") from exc


def _optional_ref(mapping: dict[str, str], key: str | None, kind: str) -> str | None:
    return _ref(mapping, key, kind) if key is not None else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and import a DivinationEngine bundle")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--schema", action="store_true", help="print the JSON Schema and exit")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(ImportBundle.model_json_schema(), indent=2))
        return
    if args.file is None:
        parser.error("file is required unless --schema is used")
    try:
        bundle = ImportBundle.model_validate_json(args.file.read_text(encoding="utf-8"))
        with SessionLocal() as session:
            result = import_bundle(session, bundle)
    except (OSError, ValidationError, ValueError, IntegrityError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
