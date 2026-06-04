"""
Orquestador de los 7 escenarios de evaluación (Tarea 2).
Se ejecuta dentro del contenedor 'orchestrator' (docker compose --profile tarea2-full up).

Cada escenario levanta producer y consumers como subprocesos Python en el mismo
contenedor, espera que terminen y guarda las métricas en results/.
"""

import csv
import json
import os
import subprocess
import sys
import time

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

from cache import clear_cache, configure_cache
from data_loader import load_data
from main import run_experiment

# ── Parámetros globales ────────────────────────────────────────────────────────
RESULTS_DIR       = os.path.join(os.path.dirname(__file__), "..", "results", "kafka")
N_REQUESTS        = int(os.getenv("N_REQUESTS", 500))
ZIPF_S            = float(os.getenv("ZIPF_S", 2.0))
DATA_PATH         = os.getenv("DATA_PATH", "../data/buildings.csv")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_HOST        = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT        = os.getenv("REDIS_PORT", "6379")

# Configuración de caché base fija para todos los escenarios Kafka
CACHE_SIZE_MB = "50"
CACHE_POLICY  = "allkeys-lru"
CACHE_TTL     = "60"

# Segundos extra después de que el producer termina para que el consumer vacíe la cola
DRAIN_WAIT = 20

os.makedirs(RESULTS_DIR, exist_ok=True)


# ── Gestión de tópicos con KafkaAdminClient ────────────────────────────────────
def _reset_topics():
    """Borra y recrea los 3 tópicos para empezar cada escenario en limpio."""
    print("  [Setup] Reseteando tópicos Kafka...")
    client = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS,
                              request_timeout_ms=15000)
    topic_names = ["queries", "queries.retry", "queries.dlq"]

    # Borrar si existen
    try:
        existing = client.list_topics()
        to_delete = [t for t in topic_names if t in existing]
        if to_delete:
            client.delete_topics(to_delete, timeout_ms=10000)
            time.sleep(4)  # esperar propagación
    except Exception as e:
        print(f"  [Setup] Aviso al borrar: {e}")

    # Crear
    new_topics = [
        NewTopic("queries",        num_partitions=4, replication_factor=1),
        NewTopic("queries.retry",  num_partitions=4, replication_factor=1),
        NewTopic("queries.dlq",    num_partitions=1, replication_factor=1),
    ]
    try:
        client.create_topics(new_topics, validate_only=False)
        print("  [Setup] Tópicos recreados.")
    except TopicAlreadyExistsError:
        print("  [Setup] Tópicos ya existían (OK).")
    except Exception as e:
        print(f"  [Setup] Aviso al crear: {e}")
    finally:
        client.close()
    time.sleep(2)


# ── Entorno base para subprocesos ──────────────────────────────────────────────
def _base_env(**extra) -> dict:
    env = {
        **os.environ,
        "PYTHONUNBUFFERED":       "1",
        "KAFKA_BOOTSTRAP_SERVERS": BOOTSTRAP_SERVERS,
        "REDIS_HOST":             REDIS_HOST,
        "REDIS_PORT":             REDIS_PORT,
        "DATA_PATH":              DATA_PATH,
        "CACHE_SIZE_MB":          CACHE_SIZE_MB,
        "CACHE_POLICY":           CACHE_POLICY,
        "CACHE_TTL":              CACHE_TTL,
        "RESULTS_DIR":            RESULTS_DIR,
        "ZIPF_S":                 str(ZIPF_S),
    }
    env.update(extra)
    return env


def _run_producer(extra: dict) -> None:
    subprocess.run([sys.executable, "-u", "kafka_producer.py"],
                   env=_base_env(**extra), check=False)


def _start_consumers(n: int, extra: dict) -> list:
    env = _base_env(**extra)
    return [subprocess.Popen([sys.executable, "-u", "kafka_consumer.py"], env=env)
            for _ in range(n)]


def _stop_consumers(procs: list):
    for p in procs:
        if p.poll() is None:
            p.terminate()
    for p in procs:
        p.wait(timeout=15)


def _load_metrics(scenario: str) -> dict:
    path = os.path.join(RESULTS_DIR, f"kafka_metrics_{scenario}.json")
    if not os.path.exists(path):
        return {"scenario": scenario}
    with open(path) as f:
        return json.load(f)


# ── Escenarios ─────────────────────────────────────────────────────────────────

def escenario_1_base() -> dict:
    """Sistema síncrono original de Tarea 1 — un solo experimento con config base."""
    print("\n=== Escenario 1: Sistema Base Síncrono ===")
    clear_cache()
    configure_cache(int(CACHE_SIZE_MB), CACHE_POLICY)
    data = load_data(DATA_PATH)
    result = run_experiment("zipf", CACHE_POLICY, int(CACHE_SIZE_MB),
                            int(CACHE_TTL), data, 1, N_REQUESTS, ZIPF_S)
    print(f"  throughput={result['throughput']:.1f} req/s  hit_rate={result['hit_rate']:.2%}")
    return {
        "scenario":       "1_base",
        "throughput":     round(result["throughput"], 2),
        "latency_p50":    round(result["latency_p50"], 6),
        "latency_p95":    round(result["latency_p95"], 6),
        "hit_rate":       round(result["hit_rate"], 4),
        "retry_rate":     0, "recovery_rate": 0,
        "dlq_rate":       0, "backlog_peak":  0,
        "recovery_time":  None, "drain_time": None,
        "total_processed": result["total_requests"],
    }


def escenario_2_kafka_1c() -> dict:
    """Kafka + 1 consumidor. Procesamiento asíncrono básico."""
    print("\n=== Escenario 2: Kafka + 1 Consumer ===")
    _reset_topics()
    scenario = "2_kafka_1c"
    consumers = _start_consumers(1, {
        "SCENARIO": scenario, "FAILURE_RATE": "0.0", "N_REQUESTS": str(N_REQUESTS),
    })
    time.sleep(3)
    _run_producer({"N_REQUESTS": str(N_REQUESTS), "DISTRIBUTION": "zipf",
                   "REQUESTS_PER_SECOND": "0"})
    time.sleep(DRAIN_WAIT)
    _stop_consumers(consumers)
    m = _load_metrics(scenario)
    print(f"  throughput={m.get('throughput', 0):.1f} req/s  hit_rate={m.get('hit_rate', 0):.2%}")
    return m


def escenario_3_kafka_nc() -> dict:
    """Kafka + múltiples consumers (1 → 2 → 4). Retorna el de 4 consumers."""
    print("\n=== Escenario 3: Kafka + Múltiples Consumers ===")
    for n in [1, 2, 4]:
        _reset_topics()
        scenario = f"3_kafka_{n}c"
        print(f"  -> {n} consumer(s)...")
        consumers = _start_consumers(n, {
            "SCENARIO": scenario, "FAILURE_RATE": "0.0",
            "N_REQUESTS": str(N_REQUESTS),
        })
        time.sleep(3)
        _run_producer({"N_REQUESTS": str(N_REQUESTS), "DISTRIBUTION": "zipf",
                       "REQUESTS_PER_SECOND": "0"})
        time.sleep(DRAIN_WAIT)
        _stop_consumers(consumers)
        m = _load_metrics(scenario)
        print(f"     {n}c → throughput={m.get('throughput', 0):.1f} req/s")
    return _load_metrics("3_kafka_4c")


def escenario_4_falla_temporal() -> dict:
    """FAILURE_RATE=1.0 durante 20s mientras el producer envía a 30 req/s."""
    print("\n=== Escenario 4: Falla Temporal ===")
    _reset_topics()
    scenario = "4_falla"
    consumers = _start_consumers(2, {
        "SCENARIO": scenario, "FAILURE_RATE": "1.0",
        "FAILURE_DURATION": "20", "N_REQUESTS": str(N_REQUESTS),
        "METRICS_INTERVAL": "10",
    })
    time.sleep(3)
    _run_producer({"N_REQUESTS": str(N_REQUESTS), "DISTRIBUTION": "zipf",
                   "REQUESTS_PER_SECOND": "30"})
    time.sleep(DRAIN_WAIT + 30)   # extra: falla dura 20s + recovery
    _stop_consumers(consumers)
    m = _load_metrics(scenario)
    print(f"  retried={m.get('retried', 0)}  dlq={m.get('dlq_count', 0)}"
          f"  recovery_time={m.get('recovery_time')}s")
    return m


def escenario_5_reintentos() -> dict:
    """50% de fallo → reintentos → eventual resolución o DLQ."""
    print("\n=== Escenario 5: Reintentos ===")
    _reset_topics()
    scenario = "5_reintentos"
    consumers = _start_consumers(2, {
        "SCENARIO": scenario, "FAILURE_RATE": "0.5",
        "MAX_RETRIES": "3", "N_REQUESTS": str(N_REQUESTS),
        "METRICS_INTERVAL": "15",
    })
    time.sleep(3)
    _run_producer({"N_REQUESTS": str(N_REQUESTS), "DISTRIBUTION": "zipf",
                   "REQUESTS_PER_SECOND": "0"})
    time.sleep(DRAIN_WAIT + 30)
    _stop_consumers(consumers)
    m = _load_metrics(scenario)
    print(f"  retry_rate={m.get('retry_rate', 0):.2%}"
          f"  recovery_rate={m.get('recovery_rate', 0):.2%}"
          f"  dlq_rate={m.get('dlq_rate', 0):.2%}")
    return m


def escenario_6_spike() -> dict:
    """Spike de tráfico: ráfaga 1× extra a mitad del stream."""
    print("\n=== Escenario 6: Spike de Tráfico ===")
    _reset_topics()
    scenario = "6_spike"
    consumers = _start_consumers(2, {
        "SCENARIO": scenario, "FAILURE_RATE": "0.0",
        "N_REQUESTS": str(N_REQUESTS), "METRICS_INTERVAL": "10",
    })
    time.sleep(3)
    _run_producer({
        "N_REQUESTS":          str(N_REQUESTS),
        "DISTRIBUTION":        "zipf",
        "REQUESTS_PER_SECOND": "30",
        "SPIKE_ENABLED":       "true",
        "SPIKE_AFTER":         str(N_REQUESTS // 3),
        "SPIKE_SIZE":          str(N_REQUESTS),
    })
    time.sleep(DRAIN_WAIT + 20)
    _stop_consumers(consumers)
    m = _load_metrics(scenario)
    print(f"  backlog_peak={_backlog_peak(m)}")
    return m


def escenario_7_recuperacion() -> dict:
    """80% de fallo durante 20s + MAX_RETRIES=3. Mide recovery_time y pérdida vs recuperación."""
    print("\n=== Escenario 7: Recuperación ante Fallos ===")
    _reset_topics()
    scenario = "7_recuperacion"
    consumers = _start_consumers(2, {
        "SCENARIO": scenario, "FAILURE_RATE": "0.8",
        "FAILURE_DURATION": "20", "MAX_RETRIES": "3", "N_REQUESTS": str(N_REQUESTS),
        "METRICS_INTERVAL": "10",
    })
    time.sleep(3)
    _run_producer({"N_REQUESTS": str(N_REQUESTS), "DISTRIBUTION": "zipf",
                   "REQUESTS_PER_SECOND": "30"})
    time.sleep(DRAIN_WAIT + 40)   # extra: falla 20s + recovery window
    _stop_consumers(consumers)
    m = _load_metrics(scenario)
    print(f"  recovered={m.get('recovered', 0)}  dlq={m.get('dlq_count', 0)}"
          f"  recovery_time={m.get('recovery_time')}s")
    return m


# ── Consolidación de resultados ────────────────────────────────────────────────
FIELDNAMES = [
    "scenario", "total_processed", "throughput",
    "latency_p50", "latency_p95", "hit_rate",
    "retry_rate", "recovery_rate", "dlq_rate",
    "backlog_peak", "recovery_time", "drain_time",
]


def _backlog_peak(m: dict) -> int:
    snaps = m.get("backlog_snapshots", [])
    return max((s[1] for s in snaps), default=0)


def _save_summary(results: list):
    path = os.path.join(RESULTS_DIR, "kafka_results_summary.csv")
    rows = []
    for m in results:
        rows.append({
            "scenario":       m.get("scenario", ""),
            "total_processed": m.get("total_processed", 0),
            "throughput":     m.get("throughput", 0),
            "latency_p50":    m.get("latency_p50", 0),
            "latency_p95":    m.get("latency_p95", 0),
            "hit_rate":       m.get("hit_rate", 0),
            "retry_rate":     m.get("retry_rate", 0),
            "recovery_rate":  m.get("recovery_rate", 0),
            "dlq_rate":       m.get("dlq_rate", 0),
            "backlog_peak":   _backlog_peak(m),
            "recovery_time":  m.get("recovery_time"),
            "drain_time":     m.get("drain_time"),
        })
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResultados guardados en {path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Tarea 2 – Evaluación con Apache Kafka")
    print(f"N_REQUESTS={N_REQUESTS}  ZIPF_S={ZIPF_S}")
    print("=" * 60)

    results = [
        escenario_1_base(),
        escenario_2_kafka_1c(),
        escenario_3_kafka_nc(),
        escenario_4_falla_temporal(),
        escenario_5_reintentos(),
        escenario_6_spike(),
        escenario_7_recuperacion(),
    ]

    _save_summary(results)

    import plot_kafka_results
    plot_kafka_results.main()
    print("\nListo. Revisa results/ para los CSV y PNG.")


if __name__ == "__main__":
    main()
