import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import models


def test_database_rejects_invalid_coin_values_and_sums(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        reading = models.Reading(title="Invariant test")
        cast = models.ReadingCast(
            reading=reading,
            cast_type="iching",
            cast_order=1,
            configuration={},
            primary_pattern="000000",
            relating_pattern="111111",
        )
        session.add_all([reading, cast])
        session.flush()
        cast.throws.append(
            models.IChingThrow(line_number=1, coin_1=1, coin_2=2, coin_3=3, line_value=6)
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with session_factory() as session:
        reading = models.Reading(title="Sum test")
        cast = models.ReadingCast(
            reading=reading,
            cast_type="iching",
            cast_order=1,
            configuration={},
            primary_pattern="000000",
            relating_pattern="111111",
        )
        session.add_all([reading, cast])
        session.flush()
        cast.throws.append(
            models.IChingThrow(line_number=1, coin_1=2, coin_2=2, coin_3=2, line_value=7)
        )
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize("pattern", ["123456", "10x010"])
def test_database_rejects_nonbinary_hexagram_patterns(
    session_factory: sessionmaker[Session], pattern: str
) -> None:
    with session_factory() as session:
        session.add(models.Hexagram(canonical_number=1, binary_pattern=pattern))
        with pytest.raises(IntegrityError):
            session.commit()


def test_database_rejects_inconsistent_cast_shape(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        reading = models.Reading(title="Bad cast")
        session.add(
            models.ReadingCast(
                reading=reading,
                cast_type="collection",
                cast_order=1,
                configuration={},
                collection_id=None,
                primary_pattern="000000",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_database_rejects_placement_owned_by_another_cast(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        collection = models.Collection(
            slug="deck", name="Deck", system_type="future-system", supports_reversals=False
        )
        first_item = models.Item(collection=collection, slug="first", name="First")
        second_item = models.Item(collection=collection, slug="second", name="Second")
        reading = models.Reading(title="Placement ownership")
        first_session = models.DeckSession(reading=reading, collection=collection)
        second_session = models.DeckSession(reading=reading, collection=collection)
        session.add_all(
            [collection, first_item, second_item, reading, first_session, second_session]
        )
        session.flush()
        first_cast = models.ReadingCast(
            reading=reading,
            cast_type="collection",
            collection_id=collection.id,
            deck_session_id=first_session.id,
            cast_order=1,
            configuration={},
        )
        second_cast = models.ReadingCast(
            reading=reading,
            cast_type="collection",
            collection_id=collection.id,
            deck_session_id=second_session.id,
            cast_order=2,
            configuration={},
        )
        session.add_all([first_cast, second_cast])
        session.flush()
        first_result = models.DrawResult(
            cast=first_cast,
            item=first_item,
            deck_session_id=first_session.id,
            draw_order=1,
            orientation="none",
        )
        second_result = models.DrawResult(
            cast=second_cast,
            item=second_item,
            deck_session_id=second_session.id,
            draw_order=1,
            orientation="none",
        )
        session.add_all([first_result, second_result])
        session.flush()
        session.add(
            models.Placement(
                cast_id=first_cast.id,
                draw_result_id=second_result.id,
                x=0,
                y=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
