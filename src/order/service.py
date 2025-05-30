import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import List
from sqlalchemy import select, func
from fastapi import Depends, HTTPException
from pydantic import UUID4
from src.order.enums import Direction, OrderType
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from src.instrument.models import Instrument
from src.balance.models import Balance
from src.core.schemas import Ok
from src.dependencies import get_session
from src.order.schemas import LimitOrderBody, MarketOrderBody, CreateOrderResponse, LimitOrder, MarketOrder, \
    L2OrderBook, Level
from src.order.models import Order
from src.transaction.models import Transaction
from src.order.enums import OrderStatus
from decimal import Decimal


DEFAULT_TICKER = "RUB"


async def create_order(*, body: LimitOrderBody | MarketOrderBody, request: Request,
                       db_session: AsyncSession = Depends(get_session)) -> CreateOrderResponse:
    # user = request.state.user

    # Шаг 1: Получаем инструмент
    instrument = await db_session.scalar(
        select(Instrument).where(Instrument.ticker == body.ticker)
    )
    if instrument is None or instrument.delisted:
        raise HTTPException(status_code=404, detail="Ticker not found or delisted")

    # # Шаг 2: Проверяем доступ
    # if instrument.access_level == "qualified_only" and user.role != "qualified":
    #     raise HTTPException(status_code=403, detail="User not authorized")

    # Шаг 3: Получаем балансы
    quote_instrument = await db_session.scalar(
        select(Instrument).where(Instrument.ticker == DEFAULT_TICKER)
    )
    if quote_instrument is None:
        raise HTTPException(status_code=500, detail="RUB instrument not found")

    balances = {
        "instrument": await db_session.scalar(
            select(Balance).where(Balance.user_id == body.user_id, Balance.instrument_id == instrument.id)
        ),
        "quote": await db_session.scalar(
            select(Balance).where(Balance.user_id == body.user_id, Balance.instrument_id == quote_instrument.id)
        )
    }
    for balance_type, balance in balances.items():
        if balance is None:
            balance = Balance(
                user_id=body.user_id,
                instrument_id=instrument.id if balance_type == "instrument" else quote_instrument.id,
                amount=0,
                locked_amount=0
            )
            balances[balance_type] = balance
            db_session.add(balance)

    # Шаг 4: Проверяем и резервируем средства/актив
    qty = body.qty
    # Определяем цену: для market будет взята из стакана, для limit — из body
    price = body.price if isinstance(body, LimitOrderBody) else 0

    required = qty * price if body.direction == Direction.buy and isinstance(body, LimitOrderBody) else qty
    available = balances["quote"].amount - balances["quote"].locked_amount if body.direction == Direction.buy else \
        balances["instrument"].amount - balances["instrument"].locked_amount
    if available < required:
        raise HTTPException(status_code=400,
                            detail=f"Insufficient {'funds' if body.direction == Direction.buy else 'stock'}")

    if body.direction == Direction.buy and isinstance(body, LimitOrderBody):
        balances["quote"].locked_amount += Decimal(str(required))
    else:
        balances["instrument"].locked_amount += qty

    # Шаг 5: Создание заявки
    if isinstance(body, MarketOrderBody):
        # Логика market
        matching_order = await db_session.scalar(
            select(Order)
            .where(
                Order.instrument_id == instrument.id,
                Order.direction == (Direction.sell if body.direction == Direction.buy else Direction.buy),
                Order.status == OrderStatus.new
            )
            .order_by(Order.price.asc() if body.direction == Direction.buy else Order.price.desc(),
                      Order.created_at.asc()).limit(1)
        )
        if matching_order is None:
            raise HTTPException(status_code=400, detail="No matching order available")

        trade_price = matching_order.price
        trade_qty = min(qty, matching_order.quantity - matching_order.filled_quantity)
        matching_order.filled_quantity += trade_qty
        matching_order.status = OrderStatus.executed if matching_order.filled_quantity == matching_order.quantity else \
            OrderStatus.partially_filled

        if body.direction == Direction.buy:
            balances["quote"].locked_amount -= trade_qty * trade_price
            balances["instrument"].amount += trade_qty
        else:
            balances["instrument"].locked_amount -= trade_qty
            balances["quote"].amount += trade_qty * trade_price

        transaction = Transaction(
            order_id=matching_order.id,
            instrument_id=instrument.id,
            price=trade_price,
            quantity=trade_qty,
            executed_at=datetime.utcnow()
        )
        db_session.add(transaction)
        order = matching_order
    else:  # LimitOrderBody
        order = Order(
            user_id=body.user_id,
            instrument_id=instrument.id,
            order_type=OrderType.limit,
            direction=body.direction,
            price=body.price,
            quantity=qty,
            filled_quantity=0,
            status=OrderStatus.new,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(order)

    # Шаг 6: Фиксация
    await db_session.commit()

    return CreateOrderResponse(order_id=order.id, status=True)


async def get_orders(*, request: Request, db_session: AsyncSession = Depends(get_session)) -> List[
    LimitOrder | MarketOrder]:
    # user = request.state.user
    # if not user:
    #     raise HTTPException(status_code=401, detail="User not authenticated")

    # Один запрос с join для всех ордеров пользователя
    result = await db_session.execute(
        select(Order, Instrument.ticker)
        .join(Instrument, Order.instrument_id == Instrument.id)
        # .where(Order.user_id == user.id)
    )
    orders_db = result.all()

    # Преобразование в Pydantic-модели
    orders = []
    for order, ticker in orders_db:
        body = LimitOrderBody(direction=Direction(order.direction), ticker=ticker, qty=order.quantity,
                              price=order.price) if order.order_type == OrderType.limit else MarketOrderBody(
            direction=Direction(order.direction), ticker=ticker, qty=int(order.quantity))
        order_model = LimitOrder(
            id=order.id,
            status=OrderStatus(order.status),
            user_id=order.user_id,
            timestamp=order.created_at,
            body=body,
            filled=int(order.filled_quantity) if order.order_type == OrderType.limit else 0
        ) if order.order_type == OrderType.limit else MarketOrder(
            id=order.id,
            status=OrderStatus(order.status),
            user_id=order.user_id,
            timestamp=order.created_at,
            body=body
        )
        orders.append(order_model)

    return orders


async def get_order(*, order_id: UUID4, request: Request,
                    db_session: AsyncSession = Depends(get_session)) -> LimitOrder | MarketOrder:
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Один запрос с join для конкретного ордера
    result = await db_session.execute(
        select(Order, Instrument.ticker)
        .join(Instrument, Order.instrument_id == Instrument.id)
        .where(Order.id == order_id, Order.user_id == user.id)
    )
    order_db = result.first()

    if not order_db:
        raise HTTPException(status_code=404, detail="Order not found or does not belong to user")

    order, ticker = order_db
    # Преобразование в Pydantic-модель
    body = LimitOrderBody(direction=Direction(order.direction), ticker=ticker, qty=order.quantity,
                          price=order.price) if order.order_type == OrderType.limit else MarketOrderBody(
        direction=Direction(order.direction), ticker=ticker, qty=int(order.quantity))
    order_model = LimitOrder(
        id=order.id,
        status=OrderStatus(order.status),
        user_id=order.user_id,
        timestamp=order.created_at,
        body=body,
        filled=int(order.filled_quantity) if order.order_type == OrderType.limit else 0
    ) if order.order_type == OrderType.limit else MarketOrder(
        id=order.id,
        status=OrderStatus(order.status),
        user_id=order.user_id,
        timestamp=order.created_at,
        body=body
    )

    return order_model


async def get_orderbook(*, ticker: str, limit: int, db_session: AsyncSession = Depends(get_session)) -> L2OrderBook:
    instrument = await db_session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    if not instrument or instrument.delisted:
        raise HTTPException(status_code=404, detail="Ticker not found or delisted")

    result = await db_session.execute(
        select(Order.price, func.sum(Order.quantity - Order.filled_quantity).label("qty"))
        .where(Order.instrument_id == instrument.id, Order.status == OrderStatus.new)
        .group_by(Order.price, Order.direction)
        .order_by(
            Order.price.desc() if Order.direction == Direction.buy else Order.price.asc()
        )
        .limit(limit)
    )
    order_levels = result.all()

    # Разделение на bid и ask уровни
    bid_levels = [
                     Level(price=int(price), qty=int(qty))
                     for price, qty in order_levels if order_levels[0][1] == Direction.buy
                 ][:limit]
    ask_levels = [
                     Level(price=int(price), qty=int(qty))
                     for price, qty in order_levels if order_levels[0][1] == Direction.sell
                 ][:limit]

    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)


async def cancel_order(*, order_id: UUID4, request: Request, db_session: AsyncSession = Depends(get_session)) -> Ok:
    # Шаг 1: Получить текущего пользователя
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Шаг 2: Проверить наличие ордера
    order = await db_session.scalar(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    if not order or order.status not in [OrderStatus.new, OrderStatus.partially_filled]:
        raise HTTPException(status_code=404 if not order else 400,
                            detail="Order not found, does not belong to user, or cannot be canceled")

    # Шаг 3: Подготовка балансов
    quote_instrument = await db_session.scalar(select(Instrument).where(Instrument.ticker == DEFAULT_TICKER))
    balances = {
        "instrument": await db_session.scalar(
            select(Balance).where(Balance.user_id == user.id, Balance.instrument_id == order.instrument_id)
        ) or Balance(user_id=user.id, instrument_id=order.instrument_id, amount=0, locked_amount=0),
        "quote": await db_session.scalar(
            select(Balance).where(Balance.user_id == user.id, Balance.instrument_id == quote_instrument.id)
        ) or Balance(user_id=user.id, instrument_id=quote_instrument.id, amount=0, locked_amount=0)
    }
    for balance in balances.values():
        db_session.add(balance)

    # Шаг 4: Разблокировать средства
    remaining_qty = order.quantity - order.filled_quantity
    locked_to_release = remaining_qty * order.price if order.direction == Direction.buy else remaining_qty
    target_balance = balances["quote"] if order.direction == Direction.buy else balances["instrument"]
    target_balance.locked_amount = max(0, target_balance.locked_amount - locked_to_release)

    # Шаг 5: Отменить ордер
    order.status = OrderStatus.canceled
    order.updated_at = datetime.utcnow()
    db_session.add(order)

    # Шаг 6: Добавить запись в transactions
    transaction = Transaction(
        order_id=order.id,
        instrument_id=order.instrument_id,
        price=order.price,
        quantity=remaining_qty,
        executed_at=datetime.utcnow(),
    )
    db_session.add(transaction)

    # Шаг 7: Фиксация изменений
    await db_session.commit()

    return Ok(success=True)

async def match_orders(db_session: AsyncSession):
    while True:
        # Получаем все pending лимитные ордеры
        result = await db_session.execute(
            select(Order)
            .where(Order.status == OrderStatus.new, Order.order_type == OrderType.limit)
            .order_by(Order.created_at)  # FIFO по времени создания
        )
        limit_orders = result.scalars().all()

        # Группировка по instrument_id с использованием defaultdict и deque
        orders_by_instrument = defaultdict(lambda: {"buy": deque(), "sell": deque()})
        for order in limit_orders:
            queue = orders_by_instrument[order.instrument_id][order.direction]
            queue.append(order)

        # Матчинг для каждого инструмента
        for instrument_id, queues in orders_by_instrument.items():
            buy_orders = queues["buy"]
            sell_orders = queues["sell"]

            # Сортировка: buy по убыванию цены, sell по возрастанию цены
            buy_orders = deque(sorted(buy_orders, key=lambda o: (-o.price, o.created_at)))
            sell_orders = deque(sorted(sell_orders, key=lambda o: (o.price, o.created_at)))

            while buy_orders and sell_orders:
                buy = buy_orders[0]
                sell = sell_orders[0]

                if buy.price >= sell.price:  # Совпадение цен
                    trade_qty = min(buy.quantity - buy.filled_quantity, sell.quantity - sell.filled_quantity)
                    if trade_qty > 0:
                        # Исполнение сделки
                        buy.filled_quantity += trade_qty
                        sell.filled_quantity += trade_qty
                        buy.status = OrderStatus.executed if buy.filled_quantity == buy.quantity else OrderStatus.partially_filled
                        sell.status = OrderStatus.executed if sell.filled_quantity == sell.quantity else OrderStatus.partially_filled
                        buy.updated_at = sell.updated_at = datetime.utcnow()  # 09:51 PM CEST = 07:51 PM UTC

                        # Обновление балансов
                        instrument = await db_session.scalar(select(Instrument).where(Instrument.id == instrument_id))
                        buy_balance = await db_session.scalar(select(Balance).where(Balance.user_id == buy.user_id, Balance.instrument_id == instrument_id))
                        sell_balance = await db_session.scalar(select(Balance).where(Balance.user_id == sell.user_id, Balance.instrument_id == instrument_id))
                        quote_instrument = await db_session.scalar(select(Instrument).where(Instrument.ticker == DEFAULT_TICKER))
                        quote_balance_buy = await db_session.scalar(select(Balance).where(Balance.user_id == buy.user_id, Balance.instrument_id == quote_instrument.id))
                        quote_balance_sell = await db_session.scalar(select(Balance).where(Balance.user_id == sell.user_id, Balance.instrument_id == quote_instrument.id))

                        if buy_balance and quote_balance_sell and quote_balance_buy and sell_balance:
                            quote_balance_buy.locked_amount -= trade_qty * buy.price
                            buy_balance.amount += trade_qty
                            quote_balance_sell.locked_amount -= trade_qty * sell.price
                            sell_balance.amount -= trade_qty

                        # Создание транзакции после изменения статуса
                        for order in [buy, sell]:
                            if order.status in [OrderStatus.executed, OrderStatus.partially_filled]:
                                transaction = Transaction(
                                    order_id=order.id,
                                    instrument_id=instrument_id,
                                    price=order.price,
                                    quantity=trade_qty,
                                    executed_at=datetime.utcnow()
                                )
                                db_session.add(transaction)

                        # Удаляем полностью исполненные ордеры из очереди
                        if buy.filled_quantity == buy.quantity:
                            buy_orders.popleft()
                        if sell.filled_quantity == sell.quantity:
                            sell_orders.popleft()
                    else:
                        if buy.filled_quantity == buy.quantity:
                            buy_orders.popleft()
                        if sell.filled_quantity == sell.quantity:
                            sell_orders.popleft()
                else:
                    break  # Если цены не совпадают, дальнейший матчинг невозможен

            # Обновление статусов в базе
            for direction in ["buy", "sell"]:
                for order in orders_by_instrument[instrument_id][direction]:
                    if order.status in [OrderStatus.partially_filled, OrderStatus.executed]:
                        db_session.add(order)

        await db_session.commit()
        await asyncio.sleep(1)  # Обновление каждую секунду
