import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, Index, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Balance(Base):
    __tablename__ = "balances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False, default=0.0)
    locked_amount: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False, default=0.0)

    __table_args__ = (
        UniqueConstraint("user_id", "instrument_id", name="uq_user_instrument_balance"),
        Index("ix_balances_user_id", "user_id"),
    )