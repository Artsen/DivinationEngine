from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.domain.casting import draw_items
from app.domain.iching import cast_iching
from app.domain.knowledge import interpretation_is_applicable
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
    deck_session_id: str | None,
    randomness: RandomSource,
) -> models.ReadingCast:
    deck_session: models.DeckSession
    if deck_session_id is None:
        deck_session = models.DeckSession(reading_id=reading.id, collection_id=collection.id)
        session.add(deck_session)
        session.flush()
    else:
        existing_session = session.get(models.DeckSession, deck_session_id)
        if existing_session is None:
            raise ValueError("deck session not found")
        if existing_session.reading_id != reading.id:
            raise ValueError("deck session belongs to a different reading")
        if existing_session.collection_id != collection.id:
            raise ValueError("deck session belongs to a different collection")
        deck_session = existing_session
    consumed_item_ids = set(
        session.scalars(
            select(models.DrawResult.item_id).where(
                models.DrawResult.deck_session_id == deck_session.id
            )
        ).all()
    )
    available_items = [item for item in collection.items if item.id not in consumed_item_ids]
    drawn = draw_items(
        available_items, count, collection.supports_reversals, reversals_enabled, randomness
    )
    cast = models.ReadingCast(
        reading_id=reading.id,
        cast_type="collection",
        collection_id=collection.id,
        deck_session_id=deck_session.id,
        cast_order=next_cast_order(session, reading.id),
        configuration={
            "count": count,
            "reversals_enabled": reversals_enabled,
            "deck_session_mode": "fresh" if deck_session_id is None else "continue",
        },
    )
    for order, result in enumerate(drawn, 1):
        cast.results.append(
            models.DrawResult(
                item_id=result.item.id,
                draw_order=order,
                orientation=result.orientation.value,
                deck_session_id=deck_session.id,
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
        "deck_session_id": cast.deck_session_id,
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
            select(models.Interpretation)
            .where(models.Interpretation.item_id.in_(item_ids))
            .options(
                selectinload(models.Interpretation.source),
                selectinload(models.Interpretation.tradition),
            )
        ).all()
        if item_ids
        else []
    )
    correspondences = (
        session.scalars(
            select(models.Correspondence)
            .where(models.Correspondence.item_id.in_(item_ids))
            .options(
                selectinload(models.Correspondence.source),
                selectinload(models.Correspondence.tradition),
            )
        ).all()
        if item_ids
        else []
    )
    interpretations_by_item: dict[str, list[models.Interpretation]] = {}
    correspondences_by_item: dict[str, list[models.Correspondence]] = {}
    for interpretation in interpretations:
        interpretations_by_item.setdefault(interpretation.item_id, []).append(interpretation)
    for correspondence in correspondences:
        correspondences_by_item.setdefault(correspondence.item_id, []).append(correspondence)

    for cast_data, cast in zip(data["casts"], reading.casts, strict=True):
        for result_data, result in zip(cast_data["draw_results"], cast.results, strict=True):
            item_interpretations = interpretations_by_item.get(result.item_id, [])
            applicable = [
                interpretation_dict(row)
                for row in item_interpretations
                if interpretation_is_applicable(result.orientation, row.interpretation_type)
            ]
            other = [
                interpretation_dict(row)
                for row in item_interpretations
                if not interpretation_is_applicable(result.orientation, row.interpretation_type)
            ]
            result_data["knowledge"] = {
                "applicable_interpretations": applicable,
                "other_interpretations": other,
                "correspondences": [
                    correspondence_dict(row)
                    for row in correspondences_by_item.get(result.item_id, [])
                ],
            }

    sources: dict[str, models.Source] = {}
    traditions: dict[str, models.Tradition] = {}
    for interpretation in interpretations:
        sources[interpretation.source.id] = interpretation.source
        if interpretation.tradition is not None:
            traditions[interpretation.tradition.id] = interpretation.tradition
    for correspondence in correspondences:
        sources[correspondence.source.id] = correspondence.source
        if correspondence.tradition is not None:
            traditions[correspondence.tradition.id] = correspondence.tradition
    data["sources"] = {
        source_id: {
            "id": source.id,
            "key": source.key,
            "title": source.title,
            "author": source.author,
            "edition": source.edition,
            "publisher": source.publisher,
            "publication_year": source.publication_year,
            "language": source.language,
            "citation": source.citation,
            "source_url": source.source_url,
            "rights_status": source.rights_status,
            "notes": source.notes,
        }
        for source_id, source in sources.items()
    }
    data["traditions"] = {
        tradition_id: {
            "id": tradition.id,
            "slug": tradition.slug,
            "name": tradition.name,
            "description": tradition.description,
        }
        for tradition_id, tradition in traditions.items()
    }
    data["notice"] = "Stored and mechanically derived facts only; no generated interpretation."
    return data


def interpretation_dict(row: models.Interpretation) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "item_id": row.item_id,
        "source_id": row.source_id,
        "tradition_id": row.tradition_id,
        "interpretation_type": row.interpretation_type,
        "exact_text": row.exact_text,
        "locator": row.locator,
        "sequence": row.sequence,
        "notes": row.notes,
    }


def correspondence_dict(row: models.Correspondence) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "item_id": row.item_id,
        "source_id": row.source_id,
        "tradition_id": row.tradition_id,
        "type": row.type,
        "value": row.value,
        "status": row.status,
        "locator": row.locator,
        "notes": row.notes,
    }
