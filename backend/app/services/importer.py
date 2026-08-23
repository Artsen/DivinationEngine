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


class ImportTrigram(BaseModel):
    key: str = Field(pattern=KEY_PATTERN)
    chinese_name: str
    pinyin: str
    glyph: str
    binary_pattern: str = Field(pattern=r"^[01]{3}$")


class ImportHexagram(BaseModel):
    key: str = Field(pattern=r"^hexagram-[0-9]{2}$")
    canonical_number: int = Field(ge=1, le=64)
    binary_pattern: str = Field(pattern=r"^[01]{6}$")
    chinese_name: str
    pinyin: str
    legge_title: str
    glyph: str
    lower_trigram: str
    upper_trigram: str


class ImportHexagramLine(BaseModel):
    key: str = Field(pattern=r"^hexagram-[0-9]{2}-line-[1-6]$")
    hexagram: str
    position: int = Field(ge=1, le=6)
    polarity: Literal["yin", "yang"]


class ImportIChingText(BaseModel):
    key: str = Field(min_length=1, max_length=220, pattern=KEY_PATTERN)
    layer: str = Field(min_length=1, max_length=80, pattern=KEY_PATTERN)
    unit_type: str = Field(min_length=1, max_length=80, pattern=KEY_PATTERN)
    hexagram: str | None = None
    trigram: str | None = None
    line_position: int | None = Field(default=None, ge=1, le=6)
    section: str | None = None
    language: str
    source: str
    tradition: str | None = None
    exact_text: str = Field(min_length=1)
    locator: str = Field(min_length=1, max_length=500)
    sequence: int = Field(ge=1)
    notes: str | None = None


class ImportIChingRelationship(BaseModel):
    key: str = Field(pattern=KEY_PATTERN)
    source_hexagram: str
    target_hexagram: str
    relationship_type: Literal["complement", "inversion", "nuclear", "single-line-change"]
    line_position: int | None = Field(default=None, ge=1, le=6)


class ImportIChingMethod(BaseModel):
    key: Literal["three-coin", "yarrow-stalk"]
    name: str
    probabilities: dict[str, str]
    source: str
    locator: str
    notes: str | None = None


class ImportBundle(BaseModel):
    format_version: Literal["1", "2"] = "1"
    collections: list[ImportCollection] = Field(default_factory=list)
    sources: list[ImportSource] = Field(default_factory=list)
    traditions: list[TraditionCreate] = Field(default_factory=list)
    interpretations: list[ImportInterpretation] = Field(default_factory=list)
    correspondences: list[ImportCorrespondence] = Field(default_factory=list)
    trigrams: list[ImportTrigram] = Field(default_factory=list)
    hexagrams: list[ImportHexagram] = Field(default_factory=list)
    hexagram_lines: list[ImportHexagramLine] = Field(default_factory=list)
    iching_texts: list[ImportIChingText] = Field(default_factory=list)
    iching_relationships: list[ImportIChingRelationship] = Field(default_factory=list)
    iching_methods: list[ImportIChingMethod] = Field(default_factory=list)

    @model_validator(mode="after")
    def stable_identities_are_unique(self) -> "ImportBundle":
        _require_unique([row.slug for row in self.collections], "collection slug")
        _require_unique([row.key for row in self.sources], "source key")
        _require_unique([row.slug for row in self.traditions], "tradition slug")
        _require_unique([row.key for row in self.interpretations], "interpretation key")
        _require_unique([row.key for row in self.correspondences], "correspondence key")
        _require_unique([row.key for row in self.trigrams], "trigram key")
        _require_unique([row.key for row in self.hexagrams], "hexagram key")
        _require_unique([row.key for row in self.hexagram_lines], "hexagram line key")
        _require_unique([row.key for row in self.iching_texts], "I Ching text key")
        _require_unique([row.key for row in self.iching_relationships], "relationship key")
        _require_unique([row.key for row in self.iching_methods], "method key")
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

        trigrams: dict[str, models.Trigram] = {}
        for trigram_data in bundle.trigrams:
            trigram_row = session.scalar(
                select(models.Trigram).where(models.Trigram.key == trigram_data.key)
            )
            values = trigram_data.model_dump()
            if trigram_row is None:
                trigram_row = models.Trigram(**values)
                session.add(trigram_row)
                created += 1
            else:
                _assign(trigram_row, values)
                updated += 1
            session.flush()
            trigrams[trigram_data.key] = trigram_row

        hexagrams: dict[str, models.Hexagram] = {}
        for hexagram_data in bundle.hexagrams:
            hexagram_row = session.scalar(
                select(models.Hexagram).where(models.Hexagram.key == hexagram_data.key)
            )
            values = hexagram_data.model_dump(exclude={"lower_trigram", "upper_trigram"})
            lower = trigrams.get(hexagram_data.lower_trigram)
            upper = trigrams.get(hexagram_data.upper_trigram)
            if lower is None or upper is None:
                raise ValueError(f"unknown trigram reference on {hexagram_data.key}")
            values.update(
                lower_trigram=hexagram_data.lower_trigram,
                upper_trigram=hexagram_data.upper_trigram,
                lower_trigram_id=lower.id,
                upper_trigram_id=upper.id,
            )
            if hexagram_row is None:
                hexagram_row = models.Hexagram(**values)
                session.add(hexagram_row)
                created += 1
            else:
                _assign(hexagram_row, values)
                updated += 1
            session.flush()
            hexagrams[hexagram_data.key] = hexagram_row

        for line_data in bundle.hexagram_lines:
            hexagram = hexagrams.get(line_data.hexagram)
            if hexagram is None:
                raise ValueError(f"unknown hexagram reference: {line_data.hexagram}")
            line_row = session.scalar(
                select(models.HexagramLine).where(models.HexagramLine.key == line_data.key)
            )
            values = line_data.model_dump(exclude={"hexagram"}) | {"hexagram_id": hexagram.id}
            if line_row is None:
                session.add(models.HexagramLine(**values))
                created += 1
            else:
                _assign(line_row, values)
                updated += 1
            session.flush()

        for text_data in bundle.iching_texts:
            hexagram = hexagrams.get(text_data.hexagram) if text_data.hexagram else None
            trigram = trigrams.get(text_data.trigram) if text_data.trigram else None
            source = _resolve_source(session, text_data.source)
            tradition = _resolve_tradition(session, text_data.tradition)
            text_row = session.scalar(
                select(models.IChingText).where(models.IChingText.key == text_data.key)
            )
            values = text_data.model_dump(exclude={"hexagram", "trigram", "source", "tradition"})
            values.update(
                hexagram_id=hexagram.id if hexagram else None,
                trigram_id=trigram.id if trigram else None,
                source_id=source.id,
                tradition_id=tradition.id if tradition else None,
            )
            if text_row is None:
                session.add(models.IChingText(**values))
                created += 1
            else:
                _assign(text_row, values)
                updated += 1
            session.flush()

        for relationship_data in bundle.iching_relationships:
            source_hexagram = hexagrams.get(relationship_data.source_hexagram)
            target_hexagram = hexagrams.get(relationship_data.target_hexagram)
            if source_hexagram is None or target_hexagram is None:
                raise ValueError(f"unknown relationship endpoint: {relationship_data.key}")
            relationship_row = session.scalar(
                select(models.IChingRelationship).where(
                    models.IChingRelationship.key == relationship_data.key
                )
            )
            values = relationship_data.model_dump(exclude={"source_hexagram", "target_hexagram"})
            values.update(
                source_hexagram_id=source_hexagram.id,
                target_hexagram_id=target_hexagram.id,
            )
            if relationship_row is None:
                session.add(models.IChingRelationship(**values))
                created += 1
            else:
                _assign(relationship_row, values)
                updated += 1
            session.flush()

        for method_data in bundle.iching_methods:
            source = _resolve_source(session, method_data.source)
            method_row = session.scalar(
                select(models.IChingMethod).where(models.IChingMethod.key == method_data.key)
            )
            values = method_data.model_dump(exclude={"source"}) | {"source_id": source.id}
            if method_row is None:
                session.add(models.IChingMethod(**values))
                created += 1
            else:
                _assign(method_row, values)
                updated += 1
            session.flush()

        result: dict[str, int | bool] = {
            "collections": len(bundle.collections),
            "items": sum(len(row.items) for row in bundle.collections),
            "sources": len(bundle.sources),
            "traditions": len(bundle.traditions),
            "interpretations": len(bundle.interpretations),
            "correspondences": len(bundle.correspondences),
            "trigrams": len(bundle.trigrams),
            "hexagrams": len(bundle.hexagrams),
            "hexagram_lines": len(bundle.hexagram_lines),
            "iching_texts": len(bundle.iching_texts),
            "iching_relationships": len(bundle.iching_relationships),
            "iching_methods": len(bundle.iching_methods),
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
