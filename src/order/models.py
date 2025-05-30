import uuid

from sqlalchemy import ForeignKey, Enum, Index, DECIMAL, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.order.enums import Direction, OrderStatus, OrderType


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    direction: Mapped[Direction] = mapped_column(Enum(Direction), nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(20, 8))
    quantity: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    filled_quantity: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False, default=0.0)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
    )