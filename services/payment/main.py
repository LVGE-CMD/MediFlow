
import os
import requests
import json
import pika
from services.common.health import health_payload
from pydantic import BaseModel, Field
from fastapi import FastAPI, Header, HTTPException

app=FastAPI(title="MediFlow Payment Service")
APPOINTMENT_URL = os.getenv(
    "APPOINTMENT_URL",
    "http://127.0.0.1:8002",
)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://mediflow:mediflow@127.0.0.1:5672/%2F",
)

EXCHANGE = "mediflow.events"

payments :list[dict]=[]
payment_idempotency: dict[str, dict] = {}
@app.get("/health")
def health():
    return health_payload("payment")



class PaymentIn(BaseModel):
    appointment_id: int
    amount: int = Field(gt=0)



def get_appointment(appointment_id:int)->dict:
    try:
        response = requests.get(
            f"{APPOINTMENT_URL}/appointments/{appointment_id}",
            timeout = 3,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code = 503,
            detail="预约服务不可用",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code = 404,
            detail="预约不存在",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code = 502,
            detail = "预约服务返回异常",
        )
    return response.json()


def cancel_appointment(appointment_id: int) -> None:
    try:
        response = requests.patch(
            f"{APPOINTMENT_URL}/appointments/{appointment_id}/cancel",
            timeout=3,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="预约服务不可用，取消失败",
        )

    if response.status_code not in (200, 409):
        raise HTTPException(
            status_code=502,
            detail="取消预约失败",
        )



def publish_payment_paid(payment: dict) -> None:
    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )
    try:
        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE,
            exchange_type="topic",
            durable=True,
        )

        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key="payment.paid",
            body=json.dumps(payment),
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()


@app.post("/payments",status_code=201)
def create_payment(
    payload: PaymentIn,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    if idempotency_key and idempotency_key in payment_idempotency:
        return payment_idempotency[idempotency_key]
    appointment = get_appointment(payload.appointment_id)
    if appointment["status"] != "booked":
        raise HTTPException(
            status_code = 409,
            detail="预约当前状态不可支付",
        )
    if payload.amount == 1:
        cancel_appointment(payload.appointment_id)
        raise HTTPException(
            status_code=402,
            detail="支付失败，预约已取消",
        )
    payment = {
        "payment_id": 2000 + len(payments) + 1,
        "appointment_id": payload.appointment_id,
        "amount": payload.amount,
        "status": "paid",
    }
    payments.append(payment)
    if idempotency_key:
        payment_idempotency[idempotency_key] = payment
    try:
        publish_payment_paid(payment)
    except pika.exceptions.AMQPError as exc:
        print(f"publish payment.paid failed: {exc}")

    return payment