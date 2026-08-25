"""Add semantic spread templates and immutable placement snapshots.

Revision ID: 98172dd0813b
Revises: c7512c41be5a
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "98172dd0813b"
down_revision: str | None = "c7512c41be5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("spreads", recreate="always") as batch:
        batch.add_column(sa.Column("origin", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("classification", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("system_types", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("source_label", sa.String(length=200), nullable=True))
    op.execute(
        "UPDATE spreads SET origin = 'legacy', classification = 'legacy-unspecified', "
        "system_types = '[]' WHERE origin IS NULL"
    )
    with op.batch_alter_table("spreads", recreate="always") as batch:
        batch.alter_column("origin", existing_type=sa.String(length=20), nullable=False)
        batch.alter_column("classification", existing_type=sa.String(length=80), nullable=False)
        batch.alter_column("system_types", existing_type=sa.JSON(), nullable=False)
        batch.create_check_constraint("ck_spread_origin", "origin IN ('builtin','custom','legacy')")
        batch.create_check_constraint("ck_spread_name_nonempty", "length(trim(name)) > 0")

    with op.batch_alter_table("spread_positions", recreate="always") as batch:
        batch.add_column(sa.Column("key", sa.String(length=120), nullable=True))
    op.execute(
        "UPDATE spread_positions SET key = 'legacy-position-' || \"order\" WHERE key IS NULL"
    )
    with op.batch_alter_table("spread_positions", recreate="always") as batch:
        batch.alter_column("key", existing_type=sa.String(length=120), nullable=False)
        batch.create_unique_constraint("uq_spread_position_key", ["spread_id", "key"])
        batch.create_check_constraint(
            "ck_spread_position_label_nonempty", "length(trim(label)) > 0"
        )

    with op.batch_alter_table("reading_casts", recreate="always") as batch:
        batch.add_column(sa.Column("spread_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("spread_key_snapshot", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("spread_name_snapshot", sa.String(length=200), nullable=True))
        batch.add_column(
            sa.Column("spread_classification_snapshot", sa.String(length=80), nullable=True)
        )
        batch.create_foreign_key(
            "fk_cast_spread", "spreads", ["spread_id"], ["id"], ondelete="RESTRICT"
        )
    op.execute(
        """
        UPDATE reading_casts SET
          spread_id = (SELECT p.spread_id FROM placements p
                       WHERE p.cast_id = reading_casts.id LIMIT 1),
          spread_key_snapshot = (SELECT s.slug FROM placements p
            JOIN spreads s ON s.id = p.spread_id
            WHERE p.cast_id = reading_casts.id LIMIT 1),
          spread_name_snapshot = (SELECT s.name FROM placements p
            JOIN spreads s ON s.id = p.spread_id
            WHERE p.cast_id = reading_casts.id LIMIT 1),
          spread_classification_snapshot = (SELECT s.classification FROM placements p
            JOIN spreads s ON s.id = p.spread_id
            WHERE p.cast_id = reading_casts.id LIMIT 1)
        WHERE EXISTS (SELECT 1 FROM placements p
                      WHERE p.cast_id = reading_casts.id AND p.spread_id IS NOT NULL)
        """
    )

    with op.batch_alter_table("placements", recreate="always") as batch:
        batch.add_column(sa.Column("position_key_snapshot", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("position_label_snapshot", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("position_description_snapshot", sa.Text(), nullable=True))
        batch.add_column(sa.Column("position_sequence_snapshot", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("x_snapshot", sa.Float(), nullable=True))
        batch.add_column(sa.Column("y_snapshot", sa.Float(), nullable=True))
        batch.add_column(sa.Column("rotation_snapshot", sa.Float(), nullable=True))
    op.execute(
        """
        UPDATE placements SET
          position_key_snapshot = (SELECT sp.key FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id),
          position_label_snapshot = (SELECT sp.label FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id),
          position_description_snapshot = (SELECT sp.description FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id),
          position_sequence_snapshot = (SELECT sp."order" FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id),
          x_snapshot = COALESCE(x, (SELECT sp.x FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id)),
          y_snapshot = COALESCE(y, (SELECT sp.y FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id)),
          rotation_snapshot = COALESCE(rotation, (SELECT sp.rotation FROM spread_positions sp
            WHERE sp.id = placements.spread_position_id))
        """
    )
    if op.get_bind().dialect.name == "sqlite":
        violations = op.get_bind().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign key violations after migration: {violations}")


def downgrade() -> None:
    with op.batch_alter_table("placements", recreate="always") as batch:
        batch.drop_column("rotation_snapshot")
        batch.drop_column("y_snapshot")
        batch.drop_column("x_snapshot")
        batch.drop_column("position_sequence_snapshot")
        batch.drop_column("position_description_snapshot")
        batch.drop_column("position_label_snapshot")
        batch.drop_column("position_key_snapshot")
    with op.batch_alter_table("reading_casts", recreate="always") as batch:
        batch.drop_constraint("fk_cast_spread", type_="foreignkey")
        batch.drop_column("spread_classification_snapshot")
        batch.drop_column("spread_name_snapshot")
        batch.drop_column("spread_key_snapshot")
        batch.drop_column("spread_id")
    with op.batch_alter_table("spread_positions", recreate="always") as batch:
        batch.drop_constraint("ck_spread_position_label_nonempty", type_="check")
        batch.drop_constraint("uq_spread_position_key", type_="unique")
        batch.drop_column("key")
    with op.batch_alter_table("spreads", recreate="always") as batch:
        batch.drop_constraint("ck_spread_name_nonempty", type_="check")
        batch.drop_constraint("ck_spread_origin", type_="check")
        batch.drop_column("source_label")
        batch.drop_column("system_types")
        batch.drop_column("classification")
        batch.drop_column("origin")
