import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "tmdb_id", name="uq_watchlist_user_tmdb"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    overview: Mapped[str | None] = mapped_column(String, nullable=True)
    genre_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    genres: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_countries: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reason_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_summary_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="watchlist")
