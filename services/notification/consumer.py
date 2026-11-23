import json
import os
import time
import pika
import redis

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://mediflow:mediflow@127.0.0.1:5672/%2F",
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

EXCHANGE = "mediflow.events"
QUEUE = "notification.payment_paid"
ROUTING_KEY = "payment.paid"

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def handle_payment_paid(channel, method, properties, body):
    event = json.loads(body)
    payment_id = event["payment_id"]

    dedupe_key = f"notify:payment:{payment_id}"

    if not redis_client.set(
        dedupe_key,
        "1",
        nx=True,
        ex=86400,
    ):
        print(f"duplicate payment.paid: {payment_id}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    print(f"notification sent for payment {payment_id}")
    channel.basic_ack(delivery_tag=method.delivery_tag)



def main():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(RABBITMQ_URL)
            )
            break
        except pika.exceptions.AMQPConnectionError:
            print("waiting for rabbitmq...")
            time.sleep(3)

    channel = connection.channel()


    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE,
        durable=True,
    )

    channel.queue_bind(
        queue=QUEUE,
        exchange=EXCHANGE,
        routing_key=ROUTING_KEY,
    )

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE,
        on_message_callback=handle_payment_paid,
    )

    print(f"waiting for {ROUTING_KEY}")
    channel.start_consuming()


if __name__ == "__main__":
    main()