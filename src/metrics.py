import time
import math


class KafkaMetricsCollector:
    """
    Agrega los resultados por escenario Kafka desde los archivos
    kafka_metrics_<scenario>.json producidos por los consumers.
    Permite comparar escenarios entre sí y contra el sistema síncrono.
    """

    def __init__(self, scenario: str, sync_throughput: float = 0):
        self.scenario = scenario
        self.sync_throughput = sync_throughput  # throughput base (Tarea 1)
        self.records: list[dict] = []

    def add_kafka_result(self, result: dict):
        """Agrega el JSON producido por kafka_consumer al final de un escenario."""
        self.records.append(result)

    def get_summary(self) -> dict:
        if not self.records:
            return {}
        last = self.records[-1]
        throughput = last.get("throughput", 0)
        return {
            "scenario":       self.scenario,
            "total_processed": last.get("total_processed", 0),
            "hit_rate":        last.get("hit_rate", 0),
            "throughput":      throughput,
            "latency_p50":     last.get("latency_p50", 0),
            "latency_p95":     last.get("latency_p95", 0),
            "retry_rate":      last.get("retry_rate", 0),
            "recovery_rate":   last.get("recovery_rate", 0),
            "dlq_rate":        last.get("dlq_rate", 0),
            "backlog_peak":    max(
                (s[1] for s in last.get("backlog_snapshots", [])),
                default=0
            ),
            "speedup_vs_sync": round(throughput / self.sync_throughput, 3)
                               if self.sync_throughput > 0 else None,
        }


class MetricsCollector:
    """
    Recolecta y calcula métricas de rendimiento del sistema de caché.
    Registra latencia por consulta, hits/misses y evictions para luego
    calcular hit rate, throughput, percentiles de latencia y cache efficiency.
    """

    def __init__(self):
        self.records = []
        self.start_time = time.time()
        self.evictions = 0

    def add_record(self, query_type, status, latency):
        """Registra el resultado de una consulta individual."""
        self.records.append({
            "query_type": query_type,
            "status": status,
            "latency": latency
        })

    def add_eviction(self, count=1):
        """Acumula el número de evictions reportadas por Redis."""
        self.evictions += count

    def percentile(self, values, p):
        """Calcula el percentil p de una lista de valores."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = math.ceil((p / 100) * len(sorted_values)) - 1
        index = max(0, min(index, len(sorted_values) - 1))
        return sorted_values[index]

    def get_summary(self, t_cache=0.001, t_db=0.02):
        """
        Calcula el resumen completo de métricas del experimento.

        t_cache: tiempo estimado de respuesta desde caché (segundos)
        t_db:    tiempo estimado de procesamiento sin caché (segundos)

        Métricas retornadas:
          - hit_rate:         hits / total
          - miss_rate:        misses / total
          - throughput:       consultas por segundo
          - latency_p50/p95:  percentiles de tiempo de respuesta
          - eviction_rate:    evictions por minuto
          - cache_efficiency: (hits*t_cache - misses*t_db) / total
        """
        total_requests = len(self.records)

        if total_requests == 0:
            return {
                "total_requests": 0, "hits": 0, "misses": 0,
                "hit_rate": 0, "miss_rate": 0, "throughput": 0,
                "latency_p50": 0, "latency_p95": 0,
                "evictions": 0, "eviction_rate": 0, "cache_efficiency": 0
            }

        hits = sum(1 for r in self.records if r["status"] == "hit")
        misses = total_requests - hits
        latencies = [r["latency"] for r in self.records]
        total_time = time.time() - self.start_time

        throughput = total_requests / total_time if total_time > 0 else 0
        eviction_rate = (self.evictions / total_requests) * 100  # evictions por cada 100 requests
        cache_efficiency = ((hits * t_cache) - (misses * t_db)) / total_requests

        return {
            "total_requests": total_requests,
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / total_requests,
            "miss_rate": misses / total_requests,
            "throughput": throughput,
            "latency_p50": self.percentile(latencies, 50),
            "latency_p95": self.percentile(latencies, 95),
            "evictions": self.evictions,
            "eviction_rate": eviction_rate,
            "cache_efficiency": cache_efficiency
        }
