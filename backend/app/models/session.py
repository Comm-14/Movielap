import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    guest_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    preference_text_creator: Mapped[str] = mapped_column(String, nullable=False)
    preference_text_guest: Mapped[str | None] = mapped_column(String, nullable=True)
    participant_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    participant_profiles: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    movies_payload: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    creator = relationship("User", back_populates="sessions_created", foreign_keys=[creator_id])
    guest = relationship("User", back_populates="sessions_joined", foreign_keys=[guest_id])
    swipes = relationship("Swipe", back_populates="session", cascade="all, delete-orphan")
