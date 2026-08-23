from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.domain.casting import draw_items
from app.domain.iching import cast_iching
from app.domain.randomness import RandomSource


def next_cast_order(session: Session, reading_id: str) -> int:
    current = session.scalar(
        select(func.max(models.ReadingCast.cast_order)).where(
            models.ReadingCast.reading_id == reading_id
        )
    )
    return (current or 0) + 1


def create_draw_cast(
    session: Session,
    reading: models.Reading,
    collection: models.Collection,
    count: int,
    reversals_enabled: bool,
    randomness: RandomSource,
) -> models.ReadingCast:
    drawn = draw_items(
        collection.items, count, collection.supports_reversals, reversals_enabled, randomness
    )
    cast = models.ReadingCast(
        reading_id=reading.id,
        cast_type="collection",
        collection_id=collection.id,
        cast_order=next_cast_order(session, reading.id),
        configuration={"count": count, "reversals_enabled": reversals_enabled},
    )
    for order, result in enumerate(drawn, 1):
        cast.results.append(
            models.DrawResult(
                item_id=result.item.id, draw_order=order, orientation=result.orientation.value
            )
        )
    session.add(cast)
    session.commit()
    return cast


def create_iching_cast(
    session: Session, reading: models.Reading, randomness: RandomSource
) -> models.ReadingCast:
    result = cast_iching(randomness)
    cast = models.ReadingCast(
        reading_id=reading.id,
        cast_type="iching",
        cast_order=next_cast_order(session, reading.id),
        configuration={"method": "three_coin"},
        primary_pattern=result.primary_pattern,
        relating_pattern=result.relating_pattern,
        changing_lines=list(result.changing_lines),
    )
    for throw in result.throws:
        cast.throws.append(
            models.IChingThrow(
                line_number=throw.line_number,
                coin_1=throw.coins[0],
                coin_2=throw.coins[1],
                coin_3=throw.coins[2],
                line_value=throw.value,
            )
        )
    session.add(cast)
    session.commit()
    return cast


def load_reading(session: Session, reading_id: str) -> models.Reading | None:
    return session.scalar(
        select(models.Reading)
        .where(models.Reading.id == reading_id)
        .options(
            selectinload(models.Reading.notes),
            selectinload(models.Reading.casts)
            .selectinload(models.ReadingCast.results)
            .selectinload(models.DrawResult.item),
            selectinload(models.Reading.casts)
            .selectinload(models.ReadingCast.results)
            .selectinload(models.DrawResult.placement)
            .selectinload(models.Placement.spread_position),
            selectinload(models.Reading.casts).selectinload(models.ReadingCast.throws),
        )
    )


def cast_dict(cast: models.ReadingCast) -> dict:
    return {
        "id": cast.id,
        "cast_type": cast.cast_type,
        "collection_id": cast.collection_id,
        "cast_order": cast.cast_order,
        "configuration": cast.configuration,
        "created_at": cast.created_at,
        "draw_results": [
            {
                "id": result.id,
                "draw_order": result.draw_order,
                "orientation": result.orientation,
                "item": {
                    "id": result.item.id,
                    "collection_id": result.item.collection_id,
                    "slug": result.item.slug,
                    "name": result.item.name,
                    "display_name": result.item.display_name,
                    "sequence": result.item.sequence,
                    "symbol": result.item.symbol,
                    "metadata": result.item.metadata_json,
                },
                "placement": placement_dict(result.placement) if result.placement else None,
            }
            for result in cast.results
        ],
        "iching": (
            {
                "method": "three_coin",
                "pattern_order": "bottom_to_top",
                "primary_pattern": cast.primary_pattern,
                "changing_lines": cast.changing_lines,
                "relating_pattern": cast.relating_pattern,
                "throws": [
                    {
                        "line_number": throw.line_number,
                        "coins": [throw.coin_1, throw.coin_2, throw.coin_3],
                        "line_value": throw.line_value,
                    }
                    for throw in cast.throws
                ],
            }
            if cast.cast_type == "iching"
            else None
        ),
    }


def placement_dict(placement: models.Placement) -> dict:
    position = placement.spread_position
    return {
        "id": placement.id,
        "spread_id": placement.spread_id,
        "spread_position_id": placement.spread_position_id,
        "x": position.x if position and placement.x is None else placement.x,
        "y": position.y if position and placement.y is None else placement.y,
        "rotation": position.rotation
        if position and placement.rotation is None
        else placement.rotation,
        "label": position.label if position else None,
    }


def reading_dict(reading: models.Reading) -> dict:
    return {
        "id": reading.id,
        "title": reading.title,
        "question": reading.question,
        "created_at": reading.created_at,
        "updated_at": reading.updated_at,
        "casts": [cast_dict(cast) for cast in reading.casts],
        "notes": [
            {
                "id": note.id,
                "reading_id": note.reading_id,
                "body": note.body,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
            }
            for note in reading.notes
        ],
    }


def context_dict(session: Session, reading: models.Reading) -> dict:
    data = reading_dict(reading)
    item_ids = [result.item_id for cast in reading.casts for result in cast.results]
    interpretations = (
        session.scalars(
            select(models.Interpretation).where(models.Interpretation.item_id.in_(item_ids))
        ).all()
        if item_ids
        else []
    )
    correspondences = (
        session.scalars(
            select(models.Correspondence).where(models.Correspondence.item_id.in_(item_ids))
        ).all()
        if item_ids
        else []
    )
    data["knowledge"] = {
        "interpretations": [
            {
                "id": row.id,
                "item_id": row.item_id,
                "source_id": row.source_id,
                "tradition_id": row.tradition_id,
                "interpretation_type": row.interpretation_type,
                "exact_text": row.exact_text,
                "locator": row.locator,
                "sequence": row.sequence,
                "notes": row.notes,
            }
            for row in interpretations
        ],
        "correspondences": [
            {
                "id": row.id,
                "item_id": row.item_id,
                "source_id": row.source_id,
                "tradition_id": row.tradition_id,
                "type": row.type,
                "value": row.value,
                "status": row.status,
                "locator": row.locator,
                "notes": row.notes,
            }
            for row in correspondences
        ],
        "notice": "Stored source-backed facts only; no generated interpretation.",
    }
    return data
