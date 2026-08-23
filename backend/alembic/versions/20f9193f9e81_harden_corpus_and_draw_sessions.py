"""Harden corpus identities, invariants, and draw sessions.

Revision ID: 20f9193f9e81
Revises: edda8e9cd334
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20f9193f9e81"
down_revision: str | None = "edda8e9cd334"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deck_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reading_id", sa.String(length=36), nullable=False),
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "reading_id", "collection_id"),
    )
    with op.batch_alter_table("collections", recreate="always") as batch:
        batch.drop_constraint("ck_collection_system", type_="check")
    with op.batch_alter_table("sources", recreate="always") as batch:
        batch.add_column(sa.Column("key", sa.String(length=160), nullable=True))
        batch.create_unique_constraint("uq_source_key", ["key"])
    with op.batch_alter_table("interpretations", recreate="always") as batch:
        batch.add_column(sa.Column("key", sa.String(length=200), nullable=True))
        batch.create_unique_constraint("uq_interpretation_key", ["key"])
        batch.drop_constraint("ck_interpretation_type", type_="check")
    with op.batch_alter_table("correspondences", recreate="always") as batch:
        batch.add_column(sa.Column("key", sa.String(length=200), nullable=True))
        batch.create_unique_constraint("uq_correspondence_key", ["key"])
    with op.batch_alter_table("hexagrams", recreate="always") as batch:
        batch.create_check_constraint(
            "ck_hexagram_pattern_binary",
            "replace(replace(binary_pattern, '0', ''), '1', '') = ''",
        )
    with op.batch_alter_table("iching_throws", recreate="always") as batch:
        batch.create_check_constraint("ck_coin_1", "coin_1 IN (2,3)")
        batch.create_check_constraint("ck_coin_2", "coin_2 IN (2,3)")
        batch.create_check_constraint("ck_coin_3", "coin_3 IN (2,3)")
        batch.create_check_constraint(
            "ck_line_value_coin_sum", "line_value = coin_1 + coin_2 + coin_3"
        )
    with op.batch_alter_table("spread_positions", recreate="always") as batch:
        batch.create_unique_constraint("uq_spread_position_identity", ["id", "spread_id"])
    with op.batch_alter_table("reading_casts", recreate="always") as batch:
        batch.add_column(sa.Column("deck_session_id", sa.String(length=36), nullable=True))
        batch.create_unique_constraint("uq_cast_deck_session_identity", ["id", "deck_session_id"])
        batch.create_foreign_key(
            "fk_cast_deck_session_scope",
            "deck_sessions",
            ["deck_session_id", "reading_id", "collection_id"],
            ["id", "reading_id", "collection_id"],
        )
        batch.create_check_constraint(
            "ck_cast_consistency",
            "(cast_type = 'collection' AND collection_id IS NOT NULL "
            "AND primary_pattern IS NULL AND relating_pattern IS NULL) OR "
            "(cast_type = 'iching' AND collection_id IS NULL "
            "AND deck_session_id IS NULL AND primary_pattern IS NOT NULL "
            "AND relating_pattern IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_cast_primary_pattern",
            "primary_pattern IS NULL OR (length(primary_pattern) = 6 AND "
            "replace(replace(primary_pattern, '0', ''), '1', '') = '')",
        )
        batch.create_check_constraint(
            "ck_cast_relating_pattern",
            "relating_pattern IS NULL OR (length(relating_pattern) = 6 AND "
            "replace(replace(relating_pattern, '0', ''), '1', '') = '')",
        )
    with op.batch_alter_table("draw_results", recreate="always") as batch:
        batch.add_column(sa.Column("deck_session_id", sa.String(length=36), nullable=True))
        batch.create_unique_constraint("uq_deck_session_item", ["deck_session_id", "item_id"])
        batch.create_unique_constraint("uq_draw_result_identity", ["id", "cast_id"])
        batch.create_foreign_key(
            "fk_result_cast_deck_session",
            "reading_casts",
            ["cast_id", "deck_session_id"],
            ["id", "deck_session_id"],
        )
    with op.batch_alter_table("placements", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_placement_spread_position",
            "spread_positions",
            ["spread_position_id", "spread_id"],
            ["id", "spread_id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_placement_draw_cast",
            "draw_results",
            ["draw_result_id", "cast_id"],
            ["id", "cast_id"],
            ondelete="CASCADE",
        )
        batch.create_check_constraint(
            "ck_placement_location",
            "(spread_id IS NULL AND spread_position_id IS NULL "
            "AND x IS NOT NULL AND y IS NOT NULL) OR "
            "(spread_id IS NOT NULL AND spread_position_id IS NOT NULL)",
        )
    if op.get_bind().dialect.name == "sqlite":
        violations = op.get_bind().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign key violations after migration: {violations}")


def downgrade() -> None:
    with op.batch_alter_table("placements", recreate="always") as batch:
        batch.drop_constraint("ck_placement_location", type_="check")
        batch.drop_constraint("fk_placement_draw_cast", type_="foreignkey")
        batch.drop_constraint("fk_placement_spread_position", type_="foreignkey")
    with op.batch_alter_table("draw_results", recreate="always") as batch:
        batch.drop_constraint("fk_result_cast_deck_session", type_="foreignkey")
        batch.drop_constraint("uq_draw_result_identity", type_="unique")
        batch.drop_constraint("uq_deck_session_item", type_="unique")
        batch.drop_column("deck_session_id")
    with op.batch_alter_table("reading_casts", recreate="always") as batch:
        batch.drop_constraint("ck_cast_relating_pattern", type_="check")
        batch.drop_constraint("ck_cast_primary_pattern", type_="check")
        batch.drop_constraint("ck_cast_consistency", type_="check")
        batch.drop_constraint("fk_cast_deck_session_scope", type_="foreignkey")
        batch.drop_constraint("uq_cast_deck_session_identity", type_="unique")
        batch.drop_column("deck_session_id")
    with op.batch_alter_table("spread_positions", recreate="always") as batch:
        batch.drop_constraint("uq_spread_position_identity", type_="unique")
    with op.batch_alter_table("iching_throws", recreate="always") as batch:
        batch.drop_constraint("ck_line_value_coin_sum", type_="check")
        batch.drop_constraint("ck_coin_3", type_="check")
        batch.drop_constraint("ck_coin_2", type_="check")
        batch.drop_constraint("ck_coin_1", type_="check")
    with op.batch_alter_table("hexagrams", recreate="always") as batch:
        batch.drop_constraint("ck_hexagram_pattern_binary", type_="check")
    with op.batch_alter_table("correspondences", recreate="always") as batch:
        batch.drop_constraint("uq_correspondence_key", type_="unique")
        batch.drop_column("key")
    with op.batch_alter_table("interpretations", recreate="always") as batch:
        batch.create_check_constraint(
            "ck_interpretation_type",
            "interpretation_type IN ('upright','reversed','divinatory','symbolism',"
            "'description','commentary')",
        )
        batch.drop_constraint("uq_interpretation_key", type_="unique")
        batch.drop_column("key")
    with op.batch_alter_table("sources", recreate="always") as batch:
        batch.drop_constraint("uq_source_key", type_="unique")
        batch.drop_column("key")
    with op.batch_alter_table("collections", recreate="always") as batch:
        batch.create_check_constraint(
            "ck_collection_system", "system_type IN ('tarot','oracle','runes')"
        )
    op.drop_table("deck_sessions")
