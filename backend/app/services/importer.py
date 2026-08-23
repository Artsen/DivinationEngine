import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.schemas.contracts import (
    CollectionCreate,
    CorrespondenceStatus,
    ItemCreate,
    SourceCreate,
    TraditionCreate,
)

KEY_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ImportCollection(CollectionCreate):
    items: list[ItemCreate] = Field(default_factory=list)


class ImportSource(SourceCreate):
    pass


class ImportInterpretation(BaseModel):
    key: str = Field(min_length=1, max_length=200, pattern=KEY_PATTERN)
    item: str = Field(description="collection-slug/item-slug")
    source: str = Field(description="stable source key")
    tradition: str | None = Field(default=None, description="tradition slug")
    interpretation_type: str = Field(min_length=1, max_length=40, pattern=KEY_PATTERN)
    exact_text: str = Field(min_length=1)
    locator: str | None = None
    sequence: int | None = None
    notes: str | None = None


class ImportCorrespondence(BaseModel):
    key: str = Field(min_length=1, max_length=200, pattern=KEY_PATTERN)
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

    @model_validator(mode="after")
    def stable_identities_are_unique(self) -> "ImportBundle":
        _require_unique([row.slug for row in self.collections], "collection slug")
        _require_unique([row.key for row in self.sources], "source key")
        _require_unique([row.slug for row in self.traditions], "tradition slug")
        _require_unique([row.key for row in self.interpretations], "interpretation key")
        _require_unique([row.key for row in self.correspondences], "correspondence key")
        item_keys = [
            f"{collection.slug}/{item.slug}"
            for collection in self.collections
            for item in collection.items
        ]
        _require_unique(item_keys, "item reference")
        return self


def _require_unique(values: list[str], kind: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {kind} in import bundle")


def import_bundle(
    session: Session, bundle: ImportBundle, *, dry_run: bool = False
) -> dict[str, int | bool]:
    created = 0
    updated = 0
    try:
        for tradition_data in bundle.traditions:
            tradition_row = session.scalar(
                select(models.Tradition).where(models.Tradition.slug == tradition_data.slug)
            )
            if tradition_row is None:
                tradition_row = models.Tradition(
                    slug=tradition_data.slug,
                    name=tradition_data.name,
                    description=tradition_data.description,
                )
                session.add(tradition_row)
                created += 1
            else:
                tradition_row.name = tradition_data.name
                tradition_row.description = tradition_data.description
                updated += 1
            session.flush()

        for source_data in bundle.sources:
            source_row = session.scalar(
                select(models.Source).where(models.Source.key == source_data.key)
            )
            source_values = source_data.model_dump()
            source_values["source_url"] = (
                str(source_data.source_url) if source_data.source_url else None
            )
            if source_row is None:
                source_row = models.Source(**source_values)
                session.add(source_row)
                created += 1
            else:
                _assign(source_row, source_values)
                updated += 1
            session.flush()

        for collection_data in bundle.collections:
            collection_row = session.scalar(
                select(models.Collection).where(models.Collection.slug == collection_data.slug)
            )
            collection_values = collection_data.model_dump(exclude={"items", "metadata"})
            if collection_row is None:
                collection_row = models.Collection(
                    **collection_values, metadata_json=collection_data.metadata
                )
                session.add(collection_row)
                created += 1
            else:
                _assign(collection_row, collection_values)
                collection_row.metadata_json = collection_data.metadata
                updated += 1
            session.flush()
            for item_data in collection_data.items:
                item = session.scalar(
                    select(models.Item).where(
                        models.Item.collection_id == collection_row.id,
                        models.Item.slug == item_data.slug,
                    )
                )
                item_values = item_data.model_dump(exclude={"metadata"})
                if item is None:
                    item = models.Item(
                        collection_id=collection_row.id,
                        **item_values,
                        metadata_json=item_data.metadata,
                    )
                    session.add(item)
                    created += 1
                else:
                    _assign(item, item_values)
                    item.metadata_json = item_data.metadata
                    updated += 1
                session.flush()

        for interpretation_data in bundle.interpretations:
            item = _resolve_item(session, interpretation_data.item)
            source = _resolve_source(session, interpretation_data.source)
            tradition = _resolve_tradition(session, interpretation_data.tradition)
            interpretation_row = session.scalar(
                select(models.Interpretation).where(
                    models.Interpretation.key == interpretation_data.key
                )
            )
            interpretation_values = interpretation_data.model_dump(
                exclude={"item", "source", "tradition"}
            )
            interpretation_values.update(
                item_id=item.id,
                source_id=source.id,
                tradition_id=tradition.id if tradition else None,
            )
            if interpretation_row is None:
                session.add(models.Interpretation(**interpretation_values))
                created += 1
            else:
                _assign(interpretation_row, interpretation_values)
                updated += 1
            session.flush()

        for correspondence_data in bundle.correspondences:
            item = _resolve_item(session, correspondence_data.item)
            source = _resolve_source(session, correspondence_data.source)
            tradition = _resolve_tradition(session, correspondence_data.tradition)
            correspondence_row = session.scalar(
                select(models.Correspondence).where(
                    models.Correspondence.key == correspondence_data.key
                )
            )
            correspondence_values = correspondence_data.model_dump(
                exclude={"item", "source", "tradition"}
            )
            correspondence_values.update(
                item_id=item.id,
                source_id=source.id,
                tradition_id=tradition.id if tradition else None,
            )
            if correspondence_row is None:
                session.add(models.Correspondence(**correspondence_values))
                created += 1
            else:
                _assign(correspondence_row, correspondence_values)
                updated += 1
            session.flush()

        result: dict[str, int | bool] = {
            "collections": len(bundle.collections),
            "items": sum(len(row.items) for row in bundle.collections),
            "sources": len(bundle.sources),
            "traditions": len(bundle.traditions),
            "interpretations": len(bundle.interpretations),
            "correspondences": len(bundle.correspondences),
            "created": created,
            "updated": updated,
            "dry_run": dry_run,
        }
        if dry_run:
            session.rollback()
        else:
            session.commit()
        return result
    except (IntegrityError, ValueError):
        session.rollback()
        raise


def _assign(row: object, values: dict) -> None:
    for name, value in values.items():
        setattr(row, name, value)


def _resolve_item(session: Session, reference: str) -> models.Item:
    try:
        collection_slug, item_slug = reference.split("/", maxsplit=1)
    except ValueError as exc:
        raise ValueError(f"invalid item reference: {reference}") from exc
    row = session.scalar(
        select(models.Item)
        .join(models.Collection)
        .where(models.Collection.slug == collection_slug, models.Item.slug == item_slug)
    )
    if row is None:
        raise ValueError(f"unknown item reference: {reference}")
    return row


def _resolve_source(session: Session, key: str) -> models.Source:
    row = session.scalar(select(models.Source).where(models.Source.key == key))
    if row is None:
        raise ValueError(f"unknown source reference: {key}")
    return row


def _resolve_tradition(session: Session, slug: str | None) -> models.Tradition | None:
    if slug is None:
        return None
    row = session.scalar(select(models.Tradition).where(models.Tradition.slug == slug))
    if row is None:
        raise ValueError(f"unknown tradition reference: {slug}")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and idempotently import a DivinationEngine bundle"
    )
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--schema", action="store_true", help="print the JSON Schema and exit")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and execute without committing changes"
    )
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(ImportBundle.model_json_schema(), indent=2))
        return
    if args.file is None:
        parser.error("file is required unless --schema is used")
    try:
        bundle = ImportBundle.model_validate_json(args.file.read_text(encoding="utf-8"))
        with SessionLocal() as session:
            result = import_bundle(session, bundle, dry_run=args.dry_run)
    except (OSError, ValidationError, ValueError, IntegrityError) as exc:
        parser.exit(1, f"Import failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
