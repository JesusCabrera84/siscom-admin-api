"""
Tests de pagos.
"""
import pytest
from fastapi import status
from app.models.payment import Payment, PaymentStatus


def test_list_payments(authenticated_client, db_session, test_client_data):
    """
    Test que lista pagos del cliente autenticado.
    """
    # Crear algunos pagos de prueba
    payment1 = Payment(
        client_id=test_client_data.id,
        amount="299.00",
        currency="MXN",
        status=PaymentStatus.SUCCESS.value,
    )
    payment2 = Payment(
        client_id=test_client_data.id,
        amount="500.00",
        currency="MXN",
        status=PaymentStatus.PENDING.value,
    )
    db_session.add_all([payment1, payment2])
    db_session.commit()
    
    # Listar pagos
    response = authenticated_client.get("/api/v1/payments/")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_payment_created_on_service_activation(
    authenticated_client,
    test_device_data,
    test_plan_data,
    db_session
):
    """
    Test que al activar un servicio se crea un pago automáticamente.
    """
    service_data = {
        "device_id": str(test_device_data.id),
        "plan_id": str(test_plan_data.id),
        "subscription_type": "MONTHLY",
    }
    
    # Contar pagos antes
    payments_before = db_session.query(Payment).filter(
        Payment.client_id == test_client_data.id
    ).count()
    
    # Activar servicio
    response = authenticated_client.post("/api/v1/services/activate", json=service_data)
    assert response.status_code == status.HTTP_201_CREATED
    
    # Verificar que se creó un pago
    payments_after = db_session.query(Payment).filter(
        Payment.client_id == test_client_data.id
    ).count()
    
    assert payments_after == payments_before + 1
    
    # Verificar que el pago está en SUCCESS (por simulación inmediata)
    payment = db_session.query(Payment).filter(
        Payment.client_id == test_client_data.id
    ).order_by(Payment.created_at.desc()).first()
    
    assert payment.status == PaymentStatus.SUCCESS.value
    assert float(payment.amount) == float(test_plan_data.price_monthly)

