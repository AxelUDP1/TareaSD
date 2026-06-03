import json
import math
import os
import random
import signal
import time
import threading

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.errors import NoBrokersAvailable

from cache import build_cache_key, get_from_cache, save_to_cache, configure_cache
from data_loader import load_data
from query_processor import execute_query

# ── Configuración ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_PATH         = os.getenv("DATA_PATH", "../data/buildings.csv")
CONSUMER_GROUP    = os.getenv("CONSUMER_GROUP", "query-processors")
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", 3))
FAILURE_RATE      = float(os.getenv("FAILURE_RATE", 0.0))   # 0.0–1.0
FAILURE_DURATION  = int(os.getenv("FAILURE_DURATION", 0))   # segundos; 0 = permanente
CACHE_SIZE_MB     = int(os.getenv("CACHE_SIZE_MB", 50))
CACHE_POLICY      = os.getenv("CACHE_POLICY", "allkeys-lru")
CACHE_TTL         = int(os.getenv("CACHE_TTL", 60))
METRICS_INTERVAL  = int(os.getenv("METRICS_INTERVAL", 30))  # segundos entre flushes
RESULTS_DIR       = os.getenv("RESULTS_DIR", "../results/kafka")
SCENARIO          = os.getenv("SCENARIO", "kafka")           # etiqueta para el archivo de salida

TOPIC_MAIN  = "queries"
TOPIC_RETRY = "queries.retry"
TOPIC_DLQ   = "queries.dlq"

ZONE_AREAS = {"Z1": 2.0, "Z2": 4.0, "Z3": 3.5, "Z4": 2.8, "Z5": 4.2}

# ── Estado global de métricas ──────────────────────────────────────────────────
_metrics = {
    "total_processed": 0,
    "cache_hits":      0,
    "cache_misses":    0,
    "retried":         0,
    "recovered":       0,
    "dlq_count":       0,
    "latencies":       [],
    "backlog_snapshots": [],
    "recovery_time":   None,   # segundos entre fin de ventana de falla y backlog=0
    "drain_time":      None,   # segundos desde pico de backlog hasta backlog=0
    "start_time":      time.time(),
}
_metrics_lock = threading.Lock()
_shutdown = threading.Event()

# Timestamp en que terminó la ventana de falla (usado para recovery_time)
_recovery_measuring: float = 0.0

# Para medir el tiempo de drenado del backlog desde su pico hasta cero
_peak_backlog: int = 0
_drain_start_time: float = 0.0


# ── Conexión a Kafka ───────────────────────────────────────────────────────────
def _connect_producer(retries=10, delay=3) -> KafkaProducer:
    for attempt in range(1, retries + 1):
        try:
            return KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=5,
            )
        except NoBrokersAvailable:
            print(f"[Consumer] Producer: Kafka no disponible, reintento {attempt}/{retries}...")
            time.sleep(delay)
    raise RuntimeError("[Consumer] No se pudo conectar al producer Kafka.")


def _connect_consumer(retries=10, delay=3) -> KafkaConsumer:
    for attempt in range(1, retries + 1):
        try:
            return KafkaConsumer(
                TOPIC_MAIN,
                TOPIC_RETRY,
                bootstrap_servers=BOOTSTRAP_SERVERS,
                group_id=CONSUMER_GROUP,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
            )
        except NoBrokersAvailable:
            print(f"[Consumer] Consumer: Kafka no disponible, reintento {attempt}/{retries}...")
            time.sleep(delay)
    raise RuntimeError("[Consumer] No se pudo conectar al consumer Kafka.")


# ── Simulación de fallos ───────────────────────────────────────────────────────
_failure_end_time: float = 0.0


def _init_failure_window():
    """Si FAILURE_DURATION > 0, activa el modo falla inmediatamente por ese tiempo."""
    global _failure_end_time
    if FAILURE_RATE > 0 and FAILURE_DURATION > 0:
        _failure_end_time = time.time() + FAILURE_DURATION
        print(f"[Consumer] Modo falla activado por {FAILURE_DURATION}s (rate={FAILURE_RATE})")


def _should_fail() -> bool:
    """Decide si esta solicitud debe fallar según FAILURE_RATE y la ventana de tiempo."""
    if FAILURE_RATE <= 0:
        return False
    if FAILURE_DURATION > 0 and time.time() > _failure_end_time:
        return False   # ventana de falla expiró
    return random.random() < FAILURE_RATE


# ── Backlog ────────────────────────────────────────────────────────────────────
def _get_backlog(consumer: KafkaConsumer, topic: str) -> int:
    try:
        partitions = consumer.partitions_for_topic(topic) or set()
        tps = [TopicPartition(topic, p) for p in partitions]
        if not tps:
            return 0
        end_offsets = consumer.end_offsets(tps)
        lag = 0
        for tp in tps:
            try:
                pos = consumer.position(tp)
                lag += max(0, end_offsets[tp] - pos)
            except Exception:
                pass
        return lag
    except Exception:
        return 0


# ── Flush de métricas ──────────────────────────────────────────────────────────
def _percentile(values: list, p: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, math.ceil(p / 100 * len(s)) - 1)
    return s[idx]


def _flush_metrics():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with _metrics_lock:
        elapsed = time.time() - _metrics["start_time"]
        total = _metrics["total_processed"]
        lats = _metrics["latencies"]
        snapshot = {
            "scenario":        SCENARIO,
            "elapsed_seconds": round(elapsed, 2),
            "total_processed": total,
            "cache_hits":      _metrics["cache_hits"],
            "cache_misses":    _metrics["cache_misses"],
            "hit_rate":        round(_metrics["cache_hits"] / total, 4) if total else 0,
            "retried":         _metrics["retried"],
            "recovered":       _metrics["recovered"],
            "dlq_count":       _metrics["dlq_count"],
            "retry_rate":      round(_metrics["retried"] / total, 4) if total else 0,
            "recovery_rate":   round(_metrics["recovered"] / _metrics["retried"], 4)
                               if _metrics["retried"] else 0,
            "dlq_rate":        round(_metrics["dlq_count"] / total, 4) if total else 0,
            "throughput":      round(total / elapsed, 2) if elapsed > 0 else 0,
            "latency_p50":     round(_percentile(lats, 50), 6),
            "latency_p95":     round(_percentile(lats, 95), 6),
            "recovery_time":   _metrics["recovery_time"],
            "drain_time":      _metrics["drain_time"],
            "backlog_snapshots": _metrics["backlog_snapshots"],
        }

    path = os.path.join(RESULTS_DIR, f"kafka_metrics_{SCENARIO}.json")
    tmp = path + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(snapshot, f, indent=2)
    os.replace(tmp, path)  # atomic on Linux — prevents partial-write corruption from concurrent consumers
    return snapshot


def _metrics_thread(consumer: KafkaConsumer):
    """Hilo que flushea métricas, registra backlog y mide recovery_time y drain_time."""
    global _recovery_measuring, _peak_backlog, _drain_start_time
    while not _shutdown.wait(timeout=METRICS_INTERVAL):
        now = time.time()
        bl = _get_backlog(consumer, TOPIC_MAIN) + _get_backlog(consumer, TOPIC_RETRY)

        # Recovery time: empieza cuando acaba la ventana de falla, termina cuando backlog=0
        if FAILURE_DURATION > 0 and _failure_end_time > 0:
            if now > _failure_end_time and _recovery_measuring == 0.0:
                _recovery_measuring = now
                print(f"[Consumer] Falla terminada, midiendo recovery_time...")
            if _recovery_measuring > 0.0 and bl == 0:
                with _metrics_lock:
                    if _metrics["recovery_time"] is None:
                        rt = round(now - _recovery_measuring, 2)
                        _metrics["recovery_time"] = rt
                        print(f"[Consumer] Recovery time: {rt}s")
                _recovery_measuring = -1.0  # marcar como ya medido

        # Drain time: desde el pico del backlog hasta backlog=0 (útil en escenario spike)
        if bl > _peak_backlog:
            _peak_backlog = bl
        elif _peak_backlog > 5 and bl < _peak_backlog and _drain_start_time == 0.0:
            _drain_start_time = now
            print(f"[Consumer] Backlog en descenso desde pico={_peak_backlog}, midiendo drain_time...")
        if _drain_start_time > 0.0 and bl == 0:
            with _metrics_lock:
                if _metrics["drain_time"] is None:
                    dt = round(now - _drain_start_time, 2)
                    _metrics["drain_time"] = dt
                    print(f"[Consumer] Drain time: {dt}s")
            _drain_start_time = -1.0  # marcar como ya medido

        with _metrics_lock:
            _metrics["backlog_snapshots"].append((round(now, 2), bl))
        snap = _flush_metrics()
        print(
            f"[Metrics] processed={snap['total_processed']} "
            f"hit={snap['hit_rate']:.2%} "
            f"retry={snap['retried']} dlq={snap['dlq_count']} "
            f"backlog={bl} "
            f"throughput={snap['throughput']:.1f} req/s"
            + (f" recovery_time={snap['recovery_time']}s" if snap['recovery_time'] else "")
        )


# ── Procesamiento de un mensaje ────────────────────────────────────────────────
def _process_message(msg: dict, producer: KafkaProducer, data: list):
    start = time.time()
    retry_count = msg.get("retry_count", 0)

    # Intentar caché primero (también en reintentos: quizás otro consumer ya lo resolvió)
    key = build_cache_key(msg)
    cached = get_from_cache(key)

    if cached is not None:
        latency = time.time() - start
        with _metrics_lock:
            _metrics["cache_hits"]      += 1
            _metrics["total_processed"] += 1
            _metrics["latencies"].append(latency)
            if retry_count > 0:
                _metrics["recovered"] += 1
        return

    # Cache miss: ejecutar query (con posible fallo simulado)
    with _metrics_lock:
        _metrics["cache_misses"] += 1

    if _should_fail():
        raise RuntimeError("Fallo simulado en el Generador de Respuestas")

    result = execute_query(data, msg, ZONE_AREAS)

    # Cachear resultado + edificaciones filtradas (igual que Tarea 1)
    zone = msg["zone"]
    conf = msg.get("confidence", 0.0)
    buildings = [b for b in data if b["zone"] == zone and b["confidence"] >= conf]
    save_to_cache(key, {"result": result, "buildings": buildings}, ttl=CACHE_TTL)

    latency = time.time() - start
    with _metrics_lock:
        _metrics["total_processed"] += 1
        _metrics["latencies"].append(latency)
        if retry_count > 0:
            _metrics["recovered"] += 1


def _handle_failure(msg: dict, producer: KafkaProducer):
    retry_count = msg.get("retry_count", 0) + 1
    if retry_count <= MAX_RETRIES:
        retry_msg = {**msg, "retry_count": retry_count}
        producer.send(TOPIC_RETRY, value=retry_msg)
        with _metrics_lock:
            _metrics["retried"] += 1
        print(
            f"[Consumer] RETRY {retry_count}/{MAX_RETRIES} "
            f"query_id={msg.get('query_id', '?')[:8]}"
        )
    else:
        producer.send(TOPIC_DLQ, value=msg)
        with _metrics_lock:
            _metrics["dlq_count"] += 1
        print(f"[Consumer] DLQ query_id={msg.get('query_id', '?')[:8]}")


# ── Loop principal ─────────────────────────────────────────────────────────────
def main():
    print(f"[Consumer] Iniciando | group={CONSUMER_GROUP} | max_retries={MAX_RETRIES} "
          f"| failure_rate={FAILURE_RATE}")

    print("[Consumer] Cargando datos de edificaciones...")
    data = load_data(DATA_PATH)
    print(f"[Consumer] {len(data)} edificaciones cargadas.")

    configure_cache(CACHE_SIZE_MB, CACHE_POLICY)
    print(f"[Consumer] Caché configurado: {CACHE_SIZE_MB}MB | {CACHE_POLICY} | TTL={CACHE_TTL}s")

    _init_failure_window()

    producer = _connect_producer()
    consumer = _connect_consumer()

    # Hilo de métricas
    t = threading.Thread(target=_metrics_thread, args=(consumer,), daemon=True)
    t.start()

    # Graceful shutdown
    def _on_signal(sig, frame):
        print("\n[Consumer] Señal recibida, cerrando...")
        _shutdown.set()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    print(f"[Consumer] Escuchando en '{TOPIC_MAIN}' y '{TOPIC_RETRY}'...")
    try:
        while not _shutdown.is_set():
            records = consumer.poll(timeout_ms=500)
            for _, messages in records.items():
                for message in messages:
                    if _shutdown.is_set():
                        break
                    msg = message.value
                    try:
                        _process_message(msg, producer, data)
                    except Exception as e:
                        _handle_failure(msg, producer)
    finally:
        consumer.close()
        producer.flush()
        producer.close()
        snap = _flush_metrics()
        print(
            f"[Consumer] Cerrado. Total={snap['total_processed']} "
            f"hits={snap['cache_hits']} misses={snap['cache_misses']} "
            f"retried={snap['retried']} recovered={snap['recovered']} "
            f"dlq={snap['dlq_count']} throughput={snap['throughput']} req/s"
            + (f" drain_time={snap['drain_time']}s" if snap['drain_time'] else "")
        )


if __name__ == "__main__":
    main()
