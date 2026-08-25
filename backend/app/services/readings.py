from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.domain.casting import draw_items
from app.domain.iching import CoinThrow, cast_by_method
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
    spread: models.SpreadDefinition | None = None,
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
        id=models.uuid4_str(),
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
        spread_id=spread.id if spread else None,
        spread_key_snapshot=spread.slug if spread else None,
        spread_name_snapshot=spread.name if spread else None,
        spread_classification_snapshot=spread.classification if spread else None,
    )
    positions = sorted(spread.positions, key=lambda position: position.order) if spread else []
    for order, result in enumerate(drawn, 1):
        draw_result = models.DrawResult(
            id=models.uuid4_str(),
            cast_id=cast.id,
            item_id=result.item.id,
            draw_order=order,
            orientation=result.orientation.value,
            deck_session_id=deck_session.id,
        )
        cast.results.append(draw_result)
        if spread:
            position = positions[order - 1]
            draw_result.placement = models.Placement(
                cast_id=cast.id,
                draw_result_id=draw_result.id,
                spread_id=spread.id,
                spread_position_id=position.id,
                position_key_snapshot=position.key,
                position_label_snapshot=position.label,
                position_description_snapshot=position.description,
                position_sequence_snapshot=position.order,
                x_snapshot=position.x,
                y_snapshot=position.y,
                rotation_snapshot=position.rotation,
            )
    session.add(cast)
    session.commit()
    return cast


def create_iching_cast(
    session: Session,
    reading: models.Reading,
    randomness: RandomSource,
    method: str = "three-coin",
) -> models.ReadingCast:
    canonical_method = "three-coin" if method == "three_coin" else method
    if canonical_method not in {"three-coin", "yarrow-stalk"}:
        raise ValueError("unsupported I Ching casting method")
    result = cast_by_method(randomness, canonical_method)  # type: ignore[arg-type]
    cast = models.ReadingCast(
        reading_id=reading.id,
        cast_type="iching",
        cast_order=next_cast_order(session, reading.id),
        configuration={"method": canonical_method},
        primary_pattern=result.primary_pattern,
        relating_pattern=result.relating_pattern,
        changing_lines=list(result.changing_lines),
    )
    for throw in result.throws:
        cast.throws.append(
            models.IChingThrow(
                line_number=throw.line_number,
                coin_1=throw.coins[0] if isinstance(throw, CoinThrow) else None,
                coin_2=throw.coins[1] if isinstance(throw, CoinThrow) else None,
                coin_3=throw.coins[2] if isinstance(throw, CoinThrow) else None,
                line_value=throw.value,
                procedure=(
                    None
                    if isinstance(throw, CoinThrow)
                    else {"manipulations": [row.__dict__ for row in throw.manipulations]}
                ),
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
                "method": cast.configuration.get("method", "three-coin"),
                "pattern_order": "bottom_to_top",
                "primary_pattern": cast.primary_pattern,
                "changing_lines": cast.changing_lines,
                "relating_pattern": cast.relating_pattern,
                "throws": [
                    {
                        "line_number": throw.line_number,
                        "coins": (
                            [throw.coin_1, throw.coin_2, throw.coin_3]
                            if throw.coin_1 is not None
                            else None
                        ),
                        "line_value": throw.line_value,
                        "procedure": throw.procedure,
                    }
                    for throw in cast.throws
                ],
            }
            if cast.cast_type == "iching"
            else None
        ),
        "spread": (
            {
                "id": cast.spread_id,
                "key": cast.spread_key_snapshot,
                "name": cast.spread_name_snapshot,
                "classification": cast.spread_classification_snapshot,
            }
            if cast.spread_id
            else None
        ),
    }


def placement_dict(placement: models.Placement) -> dict:
    position = placement.spread_position
    cast = placement.draw_result.cast
    return {
        "id": placement.id,
        "spread_id": placement.spread_id,
        "spread_position_id": placement.spread_position_id,
        "x": placement.x_snapshot
        if placement.x_snapshot is not None
        else (position.x if position and placement.x is None else placement.x),
        "y": placement.y_snapshot
        if placement.y_snapshot is not None
        else (position.y if position and placement.y is None else placement.y),
        "rotation": placement.rotation_snapshot
        if placement.rotation_snapshot is not None
        else (position.rotation if position and placement.rotation is None else placement.rotation),
        "label": placement.position_label_snapshot or (position.label if position else None),
        "spread_key": cast.spread_key_snapshot,
        "spread_name": cast.spread_name_snapshot,
        "spread_classification": cast.spread_classification_snapshot,
        "position_key": placement.position_key_snapshot or (position.key if position else None),
        "position_label": placement.position_label_snapshot
        or (position.label if position else None),
        "position_description": placement.position_description_snapshot
        if placement.position_key_snapshot
        else (position.description if position else None),
        "sequence": placement.position_sequence_snapshot or (position.order if position else None),
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
    rune_poems = (
        session.scalars(
            select(models.RunePoem)
            .where(models.RunePoem.item_id.in_(item_ids))
            .options(
                selectinload(models.RunePoem.source),
                selectinload(models.RunePoem.tradition),
            )
            .order_by(models.RunePoem.poem, models.RunePoem.sequence)
        ).all()
        if item_ids
        else []
    )
    interpretations_by_item: dict[str, list[models.Interpretation]] = {}
    correspondences_by_item: dict[str, list[models.Correspondence]] = {}
    rune_poems_by_item: dict[str, list[models.RunePoem]] = {}
    for interpretation in interpretations:
        interpretations_by_item.setdefault(interpretation.item_id, []).append(interpretation)
    for correspondence in correspondences:
        correspondences_by_item.setdefault(correspondence.item_id, []).append(correspondence)
    for poem in rune_poems:
        if poem.item_id:
            rune_poems_by_item.setdefault(poem.item_id, []).append(poem)

    iching_patterns = {
        pattern
        for cast in reading.casts
        if cast.cast_type == "iching"
        for pattern in (cast.primary_pattern, cast.relating_pattern)
        if pattern is not None
    }
    hexagrams = (
        session.scalars(
            select(models.Hexagram).where(models.Hexagram.binary_pattern.in_(iching_patterns))
        ).all()
        if iching_patterns
        else []
    )
    hexagrams_by_pattern = {row.binary_pattern: row for row in hexagrams}
    hexagram_ids = [row.id for row in hexagrams]
    iching_texts = (
        session.scalars(
            select(models.IChingText)
            .where(models.IChingText.hexagram_id.in_(hexagram_ids))
            .options(
                selectinload(models.IChingText.source),
                selectinload(models.IChingText.tradition),
            )
            .order_by(models.IChingText.sequence)
        ).all()
        if hexagram_ids
        else []
    )
    iching_texts_by_hexagram: dict[str, list[models.IChingText]] = {}
    for text_row in iching_texts:
        if text_row.hexagram_id:
            iching_texts_by_hexagram.setdefault(text_row.hexagram_id, []).append(text_row)

    for cast_data, cast in zip(data["casts"], reading.casts, strict=True):
        for result_data, result in zip(cast_data["draw_results"], cast.results, strict=True):
            item_interpretations = interpretations_by_item.get(result.item_id, [])
            # Rune poems now have a dedicated historical/editorial structure. Old
            # imports are intentionally not deleted, so suppress those legacy rows
            # whenever the structured records are available for this item.
            if rune_poems_by_item.get(result.item_id):
                item_interpretations = [
                    row for row in item_interpretations if row.interpretation_type != "rune-poem"
                ]
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
                "rune_poems": [
                    rune_poem_dict(row) for row in rune_poems_by_item.get(result.item_id, [])
                ],
            }
        if cast.cast_type == "iching" and cast_data["iching"] is not None:
            changing = set(cast.changing_lines)

            def hexagram_context(
                pattern: str | None, *, primary: bool, changing_lines: set[int] = changing
            ) -> dict | None:
                row = hexagrams_by_pattern.get(pattern or "")
                if row is None:
                    return None
                selected = []
                for text_row in iching_texts_by_hexagram.get(row.id, []):
                    include = text_row.unit_type in {"gua-ci", "great-image", "tuan"}
                    include = include or (
                        primary
                        and text_row.line_position in changing_lines
                        and text_row.unit_type in {"yao-ci", "line-image"}
                    )
                    include = include or (
                        primary
                        and len(changing_lines) == 6
                        and text_row.unit_type in {"special-use", "special-image"}
                    )
                    if include:
                        selected.append(iching_text_dict(text_row))
                return {
                    "key": row.key,
                    "canonical_number": row.canonical_number,
                    "binary_pattern": row.binary_pattern,
                    "chinese_name": row.chinese_name,
                    "pinyin": row.pinyin,
                    "legge_title": row.legge_title,
                    "glyph": row.glyph,
                    "texts": selected,
                }

            cast_data["iching"]["knowledge"] = {
                "primary": hexagram_context(cast.primary_pattern, primary=True),
                "relating": hexagram_context(cast.relating_pattern, primary=False),
                "changing_lines": sorted(changing),
                "selection_notice": (
                    "Judgment and Great Image are returned for both figures; only ordinary "
                    "changing-line texts are selected. No multi-line interpretive-school rule "
                    "is applied."
                ),
            }

    sources: dict[str, models.Source] = {}
    traditions: dict[str, models.Tradition] = {}
    for interpretation in interpretations:
        sources[interpretation.source.id] = interpretation.source
        if interpretation.tradition is not None:
            traditions[interpretation.tradition.id] = interpretation.tradition
    translation_source_ids = {
        source_id for poem in rune_poems for source_id in poem.translation_source_ids
    }
    if translation_source_ids:
        for source in session.scalars(
            select(models.Source).where(models.Source.id.in_(translation_source_ids))
        ):
            sources[source.id] = source
    for poem in rune_poems:
        sources[poem.source.id] = poem.source
        traditions[poem.tradition.id] = poem.tradition
    for correspondence in correspondences:
        sources[correspondence.source.id] = correspondence.source
        if correspondence.tradition is not None:
            traditions[correspondence.tradition.id] = correspondence.tradition
    for text_row in iching_texts:
        sources[text_row.source.id] = text_row.source
        if text_row.tradition is not None:
            traditions[text_row.tradition.id] = text_row.tradition
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


def rune_poem_dict(row: models.RunePoem) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "item_id": row.item_id,
        "source_id": row.source_id,
        "tradition_id": row.tradition_id,
        "poem": row.poem,
        "sequence": row.sequence,
        "rune_character": row.rune_character,
        "normalized_name": row.normalized_name,
        "language": row.language,
        "original_text": row.original_text,
        "latin_tag": row.latin_tag,
        "locator": row.locator,
        "mapping_status": row.mapping_status,
        "mapping_justification": row.mapping_justification,
        "editorial_translation": row.editorial_translation,
        "editorial_latin_gloss": row.editorial_latin_gloss,
        "translation_language": row.translation_language,
        "translation_type": row.translation_type,
        "translation_status": row.translation_status,
        "translator": row.translator,
        "machine_assisted": row.machine_assisted,
        "translation_source_ids": row.translation_source_ids,
        "translation_notes": row.translation_notes,
    }


def iching_text_dict(row: models.IChingText) -> dict:
    return {
        "key": row.key,
        "layer": row.layer,
        "unit_type": row.unit_type,
        "line_position": row.line_position,
        "section": row.section,
        "language": row.language,
        "source_id": row.source_id,
        "tradition_id": row.tradition_id,
        "exact_text": row.exact_text,
        "locator": row.locator,
        "sequence": row.sequence,
        "notes": row.notes,
    }
