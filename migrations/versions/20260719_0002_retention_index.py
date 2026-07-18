"""index documents for retention scans

Revision ID: 20260719_0002
Revises: 20260718_0001
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260719_0002"
down_revision: Union[str, None] = "20260718_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_retention_deleted",
        "documents",
        ["retention_until", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_retention_deleted", table_name="documents")
