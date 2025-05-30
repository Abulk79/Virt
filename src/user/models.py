import uuid

from sqlalchemy import String, Enum, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.user.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    role: Mapped["UserRole"] = mapped_column(Enum(UserRole), nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("api_key", name="uq_users_api_key"),
    )