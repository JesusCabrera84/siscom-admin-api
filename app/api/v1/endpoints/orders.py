from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_client_id
from app.db.session import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment, PaymentStatus
from app.schemas.order import OrderCreate, OrderOut

router = APIRouter()


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo pedido con sus items.
    Genera un payment asociado en estado PENDING.
    """
    # Calcular total
    total_amount = Decimal("0")
    for item in order_in.items:
        item_total = Decimal(str(item.unit_price)) * item.quantity
        total_amount += item_total

    # Crear payment en estado PENDING
    payment = Payment(
        client_id=client_id,
        amount=str(total_amount),
        currency="MXN",
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    db.flush()  # Para obtener el payment.id

    # Crear orden
    order = Order(
        client_id=client_id,
        total_amount=str(total_amount),
        status="PENDING",
        payment_id=payment.id,
    )
    db.add(order)
    db.flush()  # Para obtener el order.id

    # Crear order items
    order_items = []
    for item_in in order_in.items:
        item_total = Decimal(str(item_in.unit_price)) * item_in.quantity
        order_item = OrderItem(
            order_id=order.id,
            device_id=item_in.device_id,
            item_type=item_in.item_type.value,
            description=item_in.description,
            quantity=item_in.quantity,
            unit_price=str(item_in.unit_price),
            total_price=str(item_total),
        )
        db.add(order_item)
        order_items.append(order_item)

    db.commit()
    db.refresh(order)

    # Cargar los items para la respuesta
    order.order_items = order_items

    return order


@router.get("/", response_model=List[OrderOut])
def list_orders(
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """
    Lista las órdenes del cliente autenticado.
    Soporta paginación con limit y offset.
    """
    orders = (
        db.query(Order)
        .filter(Order.client_id == client_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return orders


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: UUID,
    client_id: UUID = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """
    Obtiene el detalle de una orden específica.
    """
    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.client_id == client_id,
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        )

    return order
