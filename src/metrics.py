import time
import math


class MetricsCollector:
    """Recolecta y resume métricas del sistema"""

    def __init__(self):
        """Inicializa los registros y contadores"""
        self.records = []
        self.start_time = time.time()
        self.evictions = 0

    def add_record(self, query_type, status, latency):
        """Guarda una métrica individual por consulta"""

        self.records.append({
            "query_type": query_type,
            "status": status,
            "latency": latency
        })

    def add_eviction(self, count=1):
        """Suma evicciones registradas"""
        self.evictions += count

    def percentile(self, values, p):
        """Calcula un percentil simple"""

        if not values:
            return 0

        sorted_values = sorted(values)
        index = math.ceil((p / 100) * len(sorted_values)) - 1
        index = max(0, min(index, len(sorted_values) - 1))

        return sorted_values[index]

    def get_summary(self, t_cache=0.001, t_db=0.02):
        """Calcula un resumen general de métricas"""

        total_requests = len(self.records)

        if total_requests == 0:
            return {
                "total_requests": 0,
                "hits": 0,
                "misses": 0,
                "hit_rate": 0,
                "miss_rate": 0,
                "throughput": 0,
                "latency_p50": 0,
                "latency_p95": 0,
                "evictions": 0,
                "eviction_rate": 0,
                "cache_efficiency": 0
            }

        hits = sum(1 for record in self.records if record["status"] == "hit")
        misses = sum(1 for record in self.records if record["status"] == "miss")

        latencies = [record["latency"] for record in self.records]

        total_time = time.time() - self.start_time
        throughput = total_requests / total_time if total_time > 0 else 0

        latency_p50 = self.percentile(latencies, 50)
        latency_p95 = self.percentile(latencies, 95)

        minutes = total_time / 60 if total_time > 0 else 1
        eviction_rate = self.evictions / minutes

        cache_efficiency = ((hits * t_cache) - (misses * t_db)) / total_requests

        return {
            "total_requests": total_requests,
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / total_requests,
            "miss_rate": misses / total_requests,
            "throughput": throughput,
            "latency_p50": latency_p50,
            "latency_p95": latency_p95,
            "evictions": self.evictions,
            "eviction_rate": eviction_rate,
            "cache_efficiency": cache_efficiency
        }