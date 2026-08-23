import sqlite3
from pathlib import Path

from alembic.config import Config
from pytest import MonkeyPatch

from alembic import command
from app.core.config import get_settings


def test_existing_milestone_database_migrates_with_data(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    database_path = tmp_path / "legacy.db"
    monkeypatch.setenv("DIVINATION_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "edda8e9cd334")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO collections
              (id, slug, name, system_type, supports_reversals, metadata, created_at, updated_at)
              VALUES ('c', 'legacy', 'Legacy', 'tarot', 1, '{}', '2026-01-01', '2026-01-01');
            INSERT INTO items
              (id, collection_id, slug, name, metadata, created_at, updated_at)
              VALUES ('i', 'c', 'alpha', 'Alpha', '{}', '2026-01-01', '2026-01-01');
            INSERT INTO readings (id, title, created_at, updated_at)
              VALUES ('r', 'Legacy reading', '2026-01-01', '2026-01-01');
            INSERT INTO reading_casts
              (id, reading_id, cast_type, collection_id, configuration, cast_order,
               created_at, changing_lines)
              VALUES ('cast', 'r', 'collection', 'c', '{}', 1, '2026-01-01', '[]');
            INSERT INTO draw_results (id, cast_id, item_id, draw_order, orientation)
              VALUES ('result', 'cast', 'i', 1, 'upright');
            INSERT INTO sources (id, title, created_at, updated_at)
              VALUES ('source', 'Legacy source', '2026-01-01', '2026-01-01');
            INSERT INTO interpretations
              (id, item_id, source_id, interpretation_type, exact_text, created_at, updated_at)
              VALUES
              ('interp', 'i', 'source', 'upright', 'Exact legacy text',
               '2026-01-01', '2026-01-01');
            INSERT INTO spreads (id, slug, name, created_at, updated_at)
              VALUES ('spread', 'one', 'One', '2026-01-01', '2026-01-01');
            INSERT INTO spread_positions (id, spread_id, label, x, y, rotation, "order")
              VALUES ('position', 'spread', 'Only', 0, 0, 0, 1);
            INSERT INTO placements
              (id, cast_id, draw_result_id, spread_id, spread_position_id)
              VALUES ('placement', 'cast', 'result', 'spread', 'position');
            INSERT INTO hexagrams
              (id, canonical_number, binary_pattern, created_at, updated_at)
              VALUES ('hex', 1, '000000', '2026-01-01', '2026-01-01');
            """
        )

    command.upgrade(config, "head")
    command.check(config)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT exact_text, key FROM interpretations WHERE id = 'interp'"
        ).fetchone() == ("Exact legacy text", None)
        assert connection.execute(
            "SELECT deck_session_id FROM reading_casts WHERE id = 'cast'"
        ).fetchone() == (None,)
    get_settings.cache_clear()
