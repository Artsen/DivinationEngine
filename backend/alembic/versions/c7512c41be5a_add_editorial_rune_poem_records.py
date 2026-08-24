"""Add source-separated rune poem records and editorial translations.

Revision ID: c7512c41be5a
Revises: 9a62b2e194c7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7512c41be5a"
down_revision: str | None = "9a62b2e194c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rune_poems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("tradition_id", sa.String(length=36), nullable=False),
        sa.Column("poem", sa.String(length=40), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("rune_character", sa.String(length=40), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("latin_tag", sa.Text(), nullable=True),
        sa.Column("locator", sa.String(length=500), nullable=False),
        sa.Column("mapping_status", sa.String(length=40), nullable=False),
        sa.Column("mapping_justification", sa.Text(), nullable=False),
        sa.Column("editorial_translation", sa.Text(), nullable=False),
        sa.Column("editorial_latin_gloss", sa.Text(), nullable=True),
        sa.Column("translation_language", sa.String(length=12), nullable=False),
        sa.Column("translation_type", sa.String(length=40), nullable=False),
        sa.Column("translation_status", sa.String(length=40), nullable=False),
        sa.Column("translator", sa.String(length=200), nullable=False),
        sa.Column("machine_assisted", sa.Boolean(), nullable=False),
        sa.Column("translation_source_ids", sa.JSON(), nullable=False),
        sa.Column("translation_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tradition_id"], ["traditions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_rune_poem_key"),
    )


def downgrade() -> None:
    op.drop_table("rune_poems")
