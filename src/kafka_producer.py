import json
import os
import time
import uuid

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from traffic_generator import generate_uniform_requests, generate_zipf_requests

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
N_REQUESTS        = int(os.getenv("N_REQUESTS", 500))
ZIPF_S            = float(os.getenv("ZIPF_S", 2.0))
DISTRIBUTION      = os.getenv("DISTRIBUTION", "zipf")   # "zipf" | "uniform"
REQUESTS_PER_SEC  = float(os.getenv("REQUESTS_PER_SECOND", 0))  # 0 = sin límite
TOPIC             = "queries"

# Para el escenario de spike: ráfaga súbita de N mensajes sin throttle
SPIKE_ENABLED     = os.getenv("SPIKE_ENABLED", "false").lower() == "true"
SPIKE_AFTER       = int(os.getenv("SPIKE_AFTER", 200))       # tras cuántos mensajes
SPIKE_SIZE        = int(os.getenv("SPIKE_SIZE", 300))         # mensajes extra del spike


def _connect(retries=10, delay=3) -> KafkaProducer:
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=5,
            )
            print(f"[Producer] Conectado a Kafka ({BOOTSTRAP_SERVERS})")
            return producer
        except NoBrokersAvailable:
            print(f"[Producer] Kafka no disponible, reintento {attempt}/{retries}...")
            time.sleep(delay)
    raise RuntimeError("[Producer] No se pudo conectar a Kafka.")


def _build_message(request: dict) -> dict:
    return {
        **request,
        "query_id":    str(uuid.uuid4()),
        "retry_count": 0,
        "created_at":  time.time(),
    }


def _publish_batch(producer: KafkaProducer, requests: list, rate: float):
    delay = 1.0 / rate if rate > 0 else 0
    for i, req in enumerate(requests):
        producer.send(TOPIC, value=_build_message(req))
        if delay:
            time.sleep(delay)
        if (i + 1) % 100 == 0:
            print(f"[Producer] {i + 1}/{len(requests)} mensajes publicados")


def main():
    producer = _connect()

    print(f"[Producer] Generando {N_REQUESTS} solicitudes (distribución: {DISTRIBUTION})")
    if DISTRIBUTION == "zipf":
        requests = generate_zipf_requests(N_REQUESTS, ZIPF_S)
    else:
        requests = generate_uniform_requests(N_REQUESTS)

    if SPIKE_ENABLED:
        # Publica hasta SPIKE_AFTER normalmente, luego inyecta la ráfaga y continúa
        print(f"[Producer] Modo spike: ráfaga de {SPIKE_SIZE} mensajes extra tras {SPIKE_AFTER}")
        _publish_batch(producer, requests[:SPIKE_AFTER], REQUESTS_PER_SEC)

        print(f"[Producer] >>> SPIKE: publicando {SPIKE_SIZE} mensajes sin throttle")
        spike_requests = generate_zipf_requests(SPIKE_SIZE, ZIPF_S)
        _publish_batch(producer, spike_requests, rate=0)

        _publish_batch(producer, requests[SPIKE_AFTER:], REQUESTS_PER_SEC)
    else:
        _publish_batch(producer, requests, REQUESTS_PER_SEC)

    producer.flush()
    total = N_REQUESTS + (SPIKE_SIZE if SPIKE_ENABLED else 0)
    print(f"[Producer] Finalizado. {total} mensajes publicados en '{TOPIC}'")


if __name__ == "__main__":
    main()
