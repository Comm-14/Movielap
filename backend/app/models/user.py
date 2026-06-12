from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    @property
    def id(self) -> int:
        return self.telegram_id

    sessions_created = relationship("Session", back_populates="creator", foreign_keys="Session.creator_id")
    sessions_joined = relationship("Session", back_populates="guest", foreign_keys="Session.guest_id")
    swipes = relationship("Swipe", back_populates="user", cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    movie_feedback = relationship("MovieFeedback", cascade="all, delete-orphan")
