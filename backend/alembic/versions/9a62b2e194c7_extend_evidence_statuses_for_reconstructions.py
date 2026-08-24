"""Extend correspondence evidence statuses for reconstructions and derived facts.

Revision ID: 9a62b2e194c7
Revises: 4161cf9c9c18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "9a62b2e194c7"
down_revision: str | None = "4161cf9c9c18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = (
    "status IN ('attested','disputed','tradition_specific','not_applicable',"
    "'not_attested','unknown')"
)
NEW = (
    "status IN ('attested','reconstructed','disputed','tradition_specific','derived',"
    "'not_applicable','not_attested','unknown')"
)


def upgrade() -> None:
    with op.batch_alter_table("correspondences") as batch_op:
        batch_op.drop_constraint("ck_correspondence_status", type_="check")
        batch_op.create_check_constraint("ck_correspondence_status", NEW)


def downgrade() -> None:
    with op.batch_alter_table("correspondences") as batch_op:
        batch_op.drop_constraint("ck_correspondence_status", type_="check")
        batch_op.create_check_constraint("ck_correspondence_status", OLD)
