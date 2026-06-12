"""group mode feedback and movie metadata

Revision ID: 20260601_0003
Revises: 20260601_0002
Create Date: 2026-06-01 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0003"
down_revision = "20260601_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("participant_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("sessions", sa.Column("participant_profiles", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("sessions", sa.Column("max_participants", sa.Integer(), nullable=False, server_default="2"))

    op.add_column("watchlist", sa.Column("genres", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("watchlist", sa.Column("runtime_minutes", sa.Integer(), nullable=True))
    op.add_column("watchlist", sa.Column("origin_countries", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("watchlist", sa.Column("match_summary_ru", sa.String(length=255), nullable=True))

    op.create_table(
        "movie_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tmdb_id", name="uq_movie_feedback_user_tmdb"),
    )


def downgrade() -> None:
    op.drop_table("movie_feedback")
    op.drop_column("watchlist", "match_summary_ru")
    op.drop_column("watchlist", "origin_countries")
    op.drop_column("watchlist", "runtime_minutes")
    op.drop_column("watchlist", "genres")
    op.drop_column("sessions", "max_participants")
    op.drop_column("sessions", "participant_profiles")
    op.drop_column("sessions", "participant_ids")
