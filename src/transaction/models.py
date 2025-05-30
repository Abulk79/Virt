import uuid

from sqlalchemy import ForeignKey, DECIMAL, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False
    )
    price: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    quantity: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    executed_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp())