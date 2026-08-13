"""Initial schema: companies and jobs tables.

Revision ID: 001
Revises:
Create Date: 2026-08-13

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("ats_provider", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("trust_tier", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("seniority", sa.String(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("legitimacy_score", sa.SmallInteger(), nullable=False, server_default="50"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("companies")
