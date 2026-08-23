from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.db.session import get_session
from app.domain.randomness import RandomSource
from app.schemas.contracts import (
    CollectionCreate,
    CollectionOut,
    CollectionPatch,
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
from app.schemas.readings import CastOut, PlacementOut, ReadingContext, ReadingDetail
from app.services.readings import (
    cast_dict,
    context_dict,
    create_draw_cast,
    create_iching_cast,
    load_reading,
    placement_dict,
    reading_dict,
)

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
        "positions": [
            {
                "id": p.id,
                "label": p.label,
                "description": p.description,
                "x": p.x,
                "y": p.y,
                "rotation": p.rotation,
                "order": p.order,
            }
            for p in row.positions
        ],
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
        select(models.SpreadDefinition).options(selectinload(models.SpreadDefinition.positions))
    ).all()
    return [spread_out(row) for row in rows]


@router.post("/spreads", response_model=SpreadOut, status_code=201)
def create_spread(body: SpreadCreate, db: DB) -> dict:
    row = models.SpreadDefinition(slug=body.slug, name=body.name, description=body.description)
    row.positions = [models.SpreadPosition(**p.model_dump()) for p in body.positions]
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
    row = db.get(models.SpreadDefinition, spread_id)
    if row is None:
        raise not_found("spread")
    changes = body.model_dump(exclude_unset=True, exclude={"positions"})
    for key, value in changes.items():
        setattr(row, key, value)
    if body.positions is not None:
        row.positions = [models.SpreadPosition(**p.model_dump()) for p in body.positions]
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
    return list(db.scalars(select(models.Reading).order_by(models.Reading.created_at.desc())).all())


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
    try:
        cast = create_draw_cast(
            db,
            reading,
            collection,
            body.count,
            body.reversals_enabled,
            body.deck_session_id,
            randomness,
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
) -> dict:
    reading = db.get(models.Reading, reading_id)
    if reading is None:
        raise not_found("reading")
    return cast_dict(create_iching_cast(db, reading, randomness))


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
    row = models.Placement(cast_id=cast_id, **body.model_dump())
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
