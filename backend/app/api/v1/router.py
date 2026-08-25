from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.db.session import get_session
from app.domain.randomness import RandomSource
from app.schemas.contracts import (
    CollectionCreate,
    CollectionOut,
    CollectionPatch,
    CorpusStatus,
    CorrespondenceCreate,
    CorrespondenceOut,
    DrawRequest,
    InterpretationCreate,
    InterpretationOut,
    ItemCreate,
    ItemOut,
    NoteCreate,
    NoteOut,
    PlacementCreate,
    ReadingCreate,
    ReadingPatch,
    ReadingSummary,
    SourceCreate,
    SourceOut,
    SpreadCreate,
    SpreadOut,
    SpreadPatch,
    TraditionCreate,
    TraditionOut,
)
from app.schemas.readings import (
    CastOut,
    ContextRunePoem,
    IChingCastRequest,
    PlacementOut,
    ReadingContext,
    ReadingDetail,
)
from app.services.assets import resolve_item_image
from app.services.readings import (
    cast_dict,
    context_dict,
    create_draw_cast,
    create_iching_cast,
    load_reading,
    placement_dict,
    reading_dict,
)
from app.services.spreads import resolved_position_values

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_session)]


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")


def commit(session: Session, conflict: str = "resource conflicts with existing data") -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=conflict) from exc


def random_source(request: Request) -> RandomSource:
    return request.app.state.random_source


def collection_out(row: models.Collection) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "system_type": row.system_type,
        "supports_reversals": row.supports_reversals,
        "metadata": row.metadata_json,
        "item_count": row.item_count,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def item_out(row: models.Item) -> dict:
    return {
        "id": row.id,
        "collection_id": row.collection_id,
        "slug": row.slug,
        "name": row.name,
        "display_name": row.display_name,
        "sequence": row.sequence,
        "symbol": row.symbol,
        "metadata": row.metadata_json,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def spread_out(row: models.SpreadDefinition) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "origin": row.origin,
        "classification": row.classification,
        "system_types": row.system_types,
        "source_label": row.source_label,
        "positions": [
            {
                "id": p.id,
                "key": p.key,
                "label": p.label,
                "description": p.description,
                "x": p.x,
                "y": p.y,
                "rotation": p.rotation,
                "order": p.order,
            }
            for p in sorted(row.positions, key=lambda position: position.order)
        ],
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/corpus-status", response_model=CorpusStatus)
def corpus_status(db: DB) -> dict[str, bool | int]:
    rws_item_count = (
        db.scalar(
            select(func.count(models.Item.id))
            .join(models.Collection)
            .where(models.Collection.slug == "rws-1909")
        )
        or 0
    )
    hexagram_count = db.scalar(select(func.count(models.Hexagram.id))) or 0
    method_count = db.scalar(select(func.count(models.IChingMethod.id))) or 0
    rune_item_count = (
        db.scalar(
            select(func.count(models.Item.id))
            .join(models.Collection)
            .where(models.Collection.slug == "elder-futhark")
        )
        or 0
    )
    rune_poem_count = db.scalar(select(func.count(models.RunePoem.id))) or 0
    return {
        "rws_ready": rws_item_count == 78,
        "rws_item_count": rws_item_count,
        "iching_ready": hexagram_count == 64 and method_count >= 2,
        "hexagram_count": hexagram_count,
        "iching_method_count": method_count,
        "runes_ready": rune_item_count == 24 and rune_poem_count == 61,
        "elder_futhark_item_count": rune_item_count,
        "rune_poem_count": rune_poem_count,
    }


@router.get("/collections", response_model=list[CollectionOut])
def list_collections(db: DB) -> list[dict]:
    rows = db.scalars(
        select(models.Collection).options(selectinload(models.Collection.items))
    ).all()
    return [collection_out(row) for row in rows]


@router.post("/collections", response_model=CollectionOut, status_code=201)
def create_collection(body: CollectionCreate, db: DB) -> dict:
    row = models.Collection(**body.model_dump(exclude={"metadata"}), metadata_json=body.metadata)
    db.add(row)
    commit(db, "collection slug already exists")
    return collection_out(row)


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: str, db: DB) -> dict:
    row = db.scalar(
        select(models.Collection)
        .where(models.Collection.id == collection_id)
        .options(selectinload(models.Collection.items))
    )
    if row is None:
        raise not_found("collection")
    return collection_out(row)


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
def patch_collection(collection_id: str, body: CollectionPatch, db: DB) -> dict:
    row = db.get(models.Collection, collection_id)
    if row is None:
        raise not_found("collection")
    changes = body.model_dump(exclude_unset=True)
    if "metadata" in changes:
        row.metadata_json = changes.pop("metadata")
    for key, value in changes.items():
        setattr(row, key, value)
    commit(db)
    return collection_out(row)


@router.get("/collections/{collection_id}/items", response_model=list[ItemOut])
def list_items(collection_id: str, db: DB) -> list[dict]:
    if db.get(models.Collection, collection_id) is None:
        raise not_found("collection")
    rows = db.scalars(
        select(models.Item)
        .where(models.Item.collection_id == collection_id)
        .order_by(models.Item.sequence, models.Item.name)
    ).all()
    return [item_out(row) for row in rows]


@router.post("/collections/{collection_id}/items", response_model=ItemOut, status_code=201)
def create_item(collection_id: str, body: ItemCreate, db: DB) -> dict:
    if db.get(models.Collection, collection_id) is None:
        raise not_found("collection")
    row = models.Item(
        collection_id=collection_id,
        **body.model_dump(exclude={"metadata"}),
        metadata_json=body.metadata,
    )
    db.add(row)
    commit(db, "item slug already exists in this collection")
    return item_out(row)


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: str, db: DB) -> dict:
    row = db.get(models.Item, item_id)
    if row is None:
        raise not_found("item")
    return item_out(row)


@router.get(
    "/items/{item_id}/image",
    responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "Image not found"}},
)
def get_item_image(item_id: str, db: DB) -> FileResponse:
    item = db.get(models.Item, item_id)
    if item is None:
        raise not_found("item image")
    resolved = resolve_item_image(item)
    if resolved is None:
        raise not_found("item image")
    path, media_type, sha256 = resolved
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{sha256}"',
        },
    )


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: DB) -> list[models.Source]:
    return list(db.scalars(select(models.Source)).all())


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(body: SourceCreate, db: DB) -> models.Source:
    values = body.model_dump()
    values["source_url"] = str(body.source_url) if body.source_url else None
    row = models.Source(**values)
    db.add(row)
    commit(db)
    return row


@router.get("/traditions", response_model=list[TraditionOut])
def list_traditions(db: DB) -> list[models.Tradition]:
    return list(db.scalars(select(models.Tradition)).all())


@router.post("/traditions", response_model=TraditionOut, status_code=201)
def create_tradition(body: TraditionCreate, db: DB) -> models.Tradition:
    row = models.Tradition(**body.model_dump())
    db.add(row)
    commit(db, "tradition slug already exists")
    return row


@router.get("/interpretations", response_model=list[InterpretationOut])
def list_interpretations(db: DB, item_id: str | None = Query(default=None)) -> list:
    statement = select(models.Interpretation)
    if item_id:
        statement = statement.where(models.Interpretation.item_id == item_id)
    return list(db.scalars(statement).all())


@router.post("/interpretations", response_model=InterpretationOut, status_code=201)
def create_interpretation(body: InterpretationCreate, db: DB) -> models.Interpretation:
    _validate_knowledge_refs(db, body.item_id, body.source_id, body.tradition_id)
    row = models.Interpretation(**body.model_dump())
    db.add(row)
    commit(db)
    return row


@router.get("/rune-poems", response_model=list[ContextRunePoem])
def list_rune_poems(db: DB, item_id: str | None = Query(default=None)) -> list[models.RunePoem]:
    statement = select(models.RunePoem).order_by(models.RunePoem.poem, models.RunePoem.sequence)
    if item_id:
        statement = statement.where(models.RunePoem.item_id == item_id)
    return list(db.scalars(statement).all())


@router.get("/correspondences", response_model=list[CorrespondenceOut])
def list_correspondences(db: DB, item_id: str | None = Query(default=None)) -> list:
    statement = select(models.Correspondence)
    if item_id:
        statement = statement.where(models.Correspondence.item_id == item_id)
    return list(db.scalars(statement).all())


@router.post("/correspondences", response_model=CorrespondenceOut, status_code=201)
def create_correspondence(body: CorrespondenceCreate, db: DB) -> models.Correspondence:
    _validate_knowledge_refs(db, body.item_id, body.source_id, body.tradition_id)
    row = models.Correspondence(**body.model_dump())
    db.add(row)
    commit(db)
    return row


def _validate_knowledge_refs(
    db: Session, item_id: str, source_id: str, tradition_id: str | None
) -> None:
    if db.get(models.Item, item_id) is None:
        raise not_found("item")
    if db.get(models.Source, source_id) is None:
        raise not_found("source")
    if tradition_id and db.get(models.Tradition, tradition_id) is None:
        raise not_found("tradition")


@router.get("/spreads", response_model=list[SpreadOut])
def list_spreads(db: DB) -> list[dict]:
    rows = db.scalars(
        select(models.SpreadDefinition)
        .options(selectinload(models.SpreadDefinition.positions))
        .order_by(models.SpreadDefinition.origin, models.SpreadDefinition.name)
    ).all()
    return [spread_out(row) for row in rows]


@router.post("/spreads", response_model=SpreadOut, status_code=201)
def create_spread(body: SpreadCreate, db: DB) -> dict:
    spread_id = models.uuid4_str()
    row = models.SpreadDefinition(
        id=spread_id,
        slug=body.slug or f"custom-{spread_id}",
        name=body.name.strip(),
        description=body.description,
        origin="custom",
        classification="custom-user-layout",
        system_types=list(dict.fromkeys(body.system_types)),
        source_label=None,
    )
    row.positions = [
        models.SpreadPosition(**values)
        for values in resolved_position_values(body.positions, spread_id=spread_id)
    ]
    db.add(row)
    commit(db, "spread slug or position order already exists")
    return spread_out(row)


@router.get("/spreads/{spread_id}", response_model=SpreadOut)
def get_spread(spread_id: str, db: DB) -> dict:
    row = db.scalar(
        select(models.SpreadDefinition)
        .where(models.SpreadDefinition.id == spread_id)
        .options(selectinload(models.SpreadDefinition.positions))
    )
    if row is None:
        raise not_found("spread")
    return spread_out(row)


@router.patch("/spreads/{spread_id}", response_model=SpreadOut)
def patch_spread(spread_id: str, body: SpreadPatch, db: DB) -> dict:
    row = db.scalar(
        select(models.SpreadDefinition)
        .where(models.SpreadDefinition.id == spread_id)
        .options(selectinload(models.SpreadDefinition.positions))
    )
    if row is None:
        raise not_found("spread")
    if row.origin != "custom":
        raise HTTPException(status_code=422, detail="built-in spreads cannot be edited")
    changes = body.model_dump(exclude_unset=True, exclude={"positions"})
    for key, value in changes.items():
        setattr(row, key, value)
    if body.positions is not None:
        if len(body.positions) != len(row.positions):
            raise HTTPException(
                status_code=422,
                detail="editing a saved spread cannot change its position count",
            )
        resolved = resolved_position_values(body.positions, spread_id=row.id)
        existing = sorted(row.positions, key=lambda position: position.order)
        existing_by_key = {position.key: position for position in existing}
        assigned: set[str] = set()
        for index, position in enumerate(existing, 1):
            position.order = 10_000 + index
            position.key = f"temporary-{position.id}"
        db.flush()
        for values in resolved:
            matched_position = existing_by_key.get(values["key"])
            if matched_position is None or matched_position.id in assigned:
                matched_position = next(
                    candidate for candidate in existing if candidate.id not in assigned
                )
            assigned.add(matched_position.id)
            for key in ("key", "label", "description", "x", "y", "rotation", "order"):
                setattr(matched_position, key, values[key])
    commit(db, "invalid or duplicate spread position")
    return spread_out(row)


@router.post("/readings", response_model=ReadingSummary, status_code=201)
def create_reading(body: ReadingCreate, db: DB) -> models.Reading:
    row = models.Reading(**body.model_dump())
    db.add(row)
    commit(db)
    return row


@router.get("/readings", response_model=list[ReadingSummary])
def list_readings(db: DB) -> list[models.Reading]:
    return list(
        db.scalars(
            select(models.Reading)
            .options(selectinload(models.Reading.casts))
            .order_by(models.Reading.created_at.desc())
        ).all()
    )


@router.get("/readings/{reading_id}", response_model=ReadingDetail)
def get_reading(reading_id: str, db: DB) -> dict:
    row = load_reading(db, reading_id)
    if row is None:
        raise not_found("reading")
    return reading_dict(row)


@router.patch("/readings/{reading_id}", response_model=ReadingSummary)
def patch_reading(reading_id: str, body: ReadingPatch, db: DB) -> models.Reading:
    row = db.get(models.Reading, reading_id)
    if row is None:
        raise not_found("reading")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    commit(db)
    return row


@router.post("/readings/{reading_id}/casts/draw", response_model=CastOut, status_code=201)
def draw_cast(
    reading_id: str,
    body: DrawRequest,
    db: DB,
    randomness: Annotated[RandomSource, Depends(random_source)],
) -> dict:
    reading = db.get(models.Reading, reading_id)
    if reading is None:
        raise not_found("reading")
    collection = db.scalar(
        select(models.Collection)
        .where(models.Collection.id == body.collection_id)
        .options(selectinload(models.Collection.items))
    )
    if collection is None:
        raise not_found("collection")
    spread = None
    if body.spread_id:
        spread = db.scalar(
            select(models.SpreadDefinition)
            .where(models.SpreadDefinition.id == body.spread_id)
            .options(selectinload(models.SpreadDefinition.positions))
        )
        if spread is None:
            raise not_found("spread")
        if spread.system_types and collection.system_type not in spread.system_types:
            raise HTTPException(status_code=422, detail="spread is not available for this system")
        if body.count != len(spread.positions):
            raise HTTPException(status_code=422, detail="draw count must match spread positions")
    try:
        cast = create_draw_cast(
            db,
            reading,
            collection,
            body.count,
            body.reversals_enabled,
            body.deck_session_id,
            randomness,
            spread,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="deck session draw conflicts with persisted results"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return cast_dict(cast)


@router.post("/readings/{reading_id}/casts/iching", response_model=CastOut, status_code=201)
def iching_cast(
    reading_id: str,
    db: DB,
    randomness: Annotated[RandomSource, Depends(random_source)],
    body: IChingCastRequest | None = None,
) -> dict:
    reading = db.get(models.Reading, reading_id)
    if reading is None:
        raise not_found("reading")
    method = body.method if body else "three-coin"
    return cast_dict(create_iching_cast(db, reading, randomness, method))


@router.post(
    "/readings/{reading_id}/casts/{cast_id}/placements",
    response_model=PlacementOut,
    status_code=201,
)
def create_placement(reading_id: str, cast_id: str, body: PlacementCreate, db: DB) -> dict:
    cast = db.get(models.ReadingCast, cast_id)
    if cast is None or cast.reading_id != reading_id:
        raise not_found("cast")
    result = db.get(models.DrawResult, body.draw_result_id)
    if result is None or result.cast_id != cast_id:
        raise HTTPException(status_code=422, detail="draw result does not belong to this cast")
    position = None
    if body.spread_position_id:
        spread = db.get(models.SpreadDefinition, body.spread_id)
        position = db.get(models.SpreadPosition, body.spread_position_id)
        if spread is None or position is None or position.spread_id != spread.id:
            raise HTTPException(status_code=422, detail="position does not belong to the spread")
        collection = db.get(models.Collection, cast.collection_id)
        if collection is None or (
            spread.system_types and collection.system_type not in spread.system_types
        ):
            raise HTTPException(status_code=422, detail="spread is not available for this system")
        if cast.spread_id and cast.spread_id != spread.id:
            raise HTTPException(status_code=422, detail="cast already uses a different spread")
        if cast.spread_id is None:
            cast.spread_id = spread.id
            cast.spread_key_snapshot = spread.slug
            cast.spread_name_snapshot = spread.name
            cast.spread_classification_snapshot = spread.classification
    row = models.Placement(
        cast_id=cast_id,
        **body.model_dump(),
        position_key_snapshot=position.key if position else None,
        position_label_snapshot=position.label if position else None,
        position_description_snapshot=position.description if position else None,
        position_sequence_snapshot=position.order if position else None,
        x_snapshot=position.x if position else body.x,
        y_snapshot=position.y if position else body.y,
        rotation_snapshot=position.rotation if position else body.rotation,
    )
    db.add(row)
    commit(db, "draw result or spread position is already placed")
    row.spread_position = position
    return placement_dict(row)


@router.post("/readings/{reading_id}/notes", response_model=NoteOut, status_code=201)
def create_note(reading_id: str, body: NoteCreate, db: DB) -> models.ReadingNote:
    if db.get(models.Reading, reading_id) is None:
        raise not_found("reading")
    row = models.ReadingNote(reading_id=reading_id, body=body.body)
    db.add(row)
    commit(db)
    return row


@router.patch("/readings/{reading_id}/notes/{note_id}", response_model=NoteOut)
def patch_note(reading_id: str, note_id: str, body: NoteCreate, db: DB) -> models.ReadingNote:
    row = db.get(models.ReadingNote, note_id)
    if row is None or row.reading_id != reading_id:
        raise not_found("note")
    row.body = body.body
    commit(db)
    return row


@router.delete("/readings/{reading_id}/notes/{note_id}", status_code=204)
def delete_note(reading_id: str, note_id: str, db: DB) -> Response:
    row = db.get(models.ReadingNote, note_id)
    if row is None or row.reading_id != reading_id:
        raise not_found("note")
    db.delete(row)
    commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/readings/{reading_id}/context", response_model=ReadingContext)
def get_context(reading_id: str, db: DB) -> dict:
    row = load_reading(db, reading_id)
    if row is None:
        raise not_found("reading")
    return context_dict(db, row)
