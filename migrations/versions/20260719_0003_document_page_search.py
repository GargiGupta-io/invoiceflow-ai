"""store searchable document pages

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260719_0003"
down_revision: Union[str, None] = "20260719_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_pages",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(length=20), nullable=False),
        sa.Column(
            "warnings",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "page_number > 0",
            name=op.f("ck_document_pages_positive_page_number"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["documents.id", "documents.organization_id"],
            name="fk_document_pages_document_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_pages")),
        sa.UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_pages_page",
        ),
    )
    op.create_index(
        "ix_document_pages_organization_document",
        "document_pages",
        ["organization_id", "document_id", "page_number"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_document_pages_text_search "
            "ON document_pages USING gin (to_tsvector('english', text_content))"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_document_pages_text_search")
    op.drop_index(
        "ix_document_pages_organization_document",
        table_name="document_pages",
    )
    op.drop_table("document_pages")
