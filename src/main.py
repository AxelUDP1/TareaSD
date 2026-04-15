import time
import csv

from data_loader import load_data
from traffic_generator import generate_uniform_requests, generate_zipf_requests
from cache import (
    build_cache_key,
    get_from_cache,
    save_to_cache,
    clear_cache,
    configure_cache,
    get_cache_stats
)
from query_processor import execute_query
from metrics import MetricsCollector


ZONE_AREAS = {
    "Z1": 2.0,
    "Z2": 4.0,
    "Z3": 3.5,
    "Z4": 2.8,
    "Z5": 4.2
}


def run_experiment(distribution, policy, cache_size, ttl, data, run_id):
    """Ejecuta una configuración completa"""

    clear_cache()
    configure_cache(cache_size, policy)

    metrics = MetricsCollector()

    if distribution == "uniform":
        requests = generate_uniform_requests(100)
    else:
        requests = generate_zipf_requests(100)

    for request in requests:
        start_time = time.time()

        key = build_cache_key(request)
        cached = get_from_cache(key)

        if cached is not None:
            latency = time.time() - start_time
            metrics.add_record(request["query_type"], "hit", latency)
        else:
            result = execute_query(data, request, ZONE_AREAS)
            save_to_cache(key, result, ttl=ttl)

            latency = time.time() - start_time
            metrics.add_record(request["query_type"], "miss", latency)

    redis_stats = get_cache_stats()
    metrics.add_eviction(redis_stats["evicted_keys"])

    summary = metrics.get_summary()

    summary.update({
        "run_id": run_id,
        "distribution": distribution,
        "policy": policy,
        "cache_size_mb": cache_size,
        "ttl": ttl,
        "redis_hits": redis_stats["keyspace_hits"],
        "redis_misses": redis_stats["keyspace_misses"]
    })

    return summary


def main():
    print("Cargando datos...")
    data = load_data("../data/buildings.csv")

    distributions = ["uniform", "zipf"]
    policies = ["allkeys-lru", "allkeys-lfu"]
    cache_sizes = [50, 200]
    ttls = [15, 60]

    results = []

    run_id = 1

    for dist in distributions:
        for policy in policies:
            for size in cache_sizes:
                for ttl in ttls:

                    print(f"\nRUN {run_id} | {dist} | {policy} | {size}MB | TTL={ttl}")

                    summary = run_experiment(
                        dist, policy, size, ttl, data, run_id
                    )

                    print(summary)

                    results.append(summary)
                    run_id += 1

    save_results(results)


def save_results(results):
    """Guarda resultados en CSV"""

    keys = results[0].keys()

    with open("../results/results_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    print("\nResultados guardados en results/results_summary.csv")


if __name__ == "__main__":
    main()