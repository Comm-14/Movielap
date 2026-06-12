"""session movies and watchlist metadata

Revision ID: 20260601_0002
Revises: 20260517_0001
Create Date: 2026-06-01 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0002"
down_revision = "20260517_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("movies_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column("watchlist", sa.Column("original_title", sa.String(length=255), nullable=True))
    op.add_column("watchlist", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("watchlist", sa.Column("poster_path", sa.String(length=255), nullable=True))
    op.add_column("watchlist", sa.Column("vote_average", sa.Float(), nullable=True))
    op.add_column("watchlist", sa.Column("overview", sa.String(), nullable=True))
    op.add_column("watchlist", sa.Column("genre_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("watchlist", sa.Column("reason_ru", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("watchlist", "reason_ru")
    op.drop_column("watchlist", "genre_ids")
    op.drop_column("watchlist", "overview")
    op.drop_column("watchlist", "vote_average")
    op.drop_column("watchlist", "poster_path")
    op.drop_column("watchlist", "year")
    op.drop_column("watchlist", "original_title")
    op.drop_column("sessions", "movies_payload")
