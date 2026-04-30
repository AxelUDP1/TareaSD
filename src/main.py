import os
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


def run_experiment(distribution, policy, cache_size, ttl, data, run_id, n_requests, zipf_s):
    """
    Ejecuta un experimento completo con la configuración indicada.
    Retorna un diccionario con todas las métricas del experimento.
    """
    clear_cache()
    configure_cache(cache_size, policy)

    # Snapshot antes del experimento para calcular delta de evictions
    stats_before = get_cache_stats()

    metrics = MetricsCollector()

    if distribution == "uniform":
        requests = generate_uniform_requests(n_requests)
    else:
        requests = generate_zipf_requests(n_requests, s=zipf_s)

    for request in requests:
        start_time = time.time()

        key = build_cache_key(request)
        cached = get_from_cache(key)

        if cached is not None:
            latency = time.time() - start_time
            metrics.add_record(request["query_type"], "hit", latency)
        else:
            result = execute_query(data, request, ZONE_AREAS)

            # Se almacena el resultado junto a los registros filtrados de la zona,
            # simulando un caché que pre-filtra datos para reutilización en queries
            # posteriores de la misma zona/confianza (tamaño realista ~5-15KB por entrada)
            zone = request["zone"]
            confidence = request.get("confidence", 0.0)
            buildings = [b for b in data if b["zone"] == zone and b["confidence"] >= confidence]
            save_to_cache(key, {"result": result, "buildings": buildings}, ttl=ttl)

            latency = time.time() - start_time
            metrics.add_record(request["query_type"], "miss", latency)

    redis_stats = get_cache_stats()
    evictions_this_run = redis_stats["evicted_keys"] - stats_before["evicted_keys"]
    metrics.add_eviction(evictions_this_run)

    summary = metrics.get_summary()
    summary.update({
        "run_id": run_id,
        "distribution": distribution,
        "policy": policy,
        "cache_size_mb": cache_size,
        "cache_size_label": f"{int(cache_size)}MB",
        "ttl": ttl,
        "n_requests": n_requests,
        "zipf_s": zipf_s,
        "redis_hits": redis_stats["keyspace_hits"],
        "redis_misses": redis_stats["keyspace_misses"]
    })

    return summary


def main():
    # Parámetros configurables via variables de entorno
    n_requests = int(os.environ.get("N_REQUESTS", 500))
    zipf_s = float(os.environ.get("ZIPF_S", 2.0))
    data_path = os.environ.get("DATA_PATH", "../data/buildings.csv")

    print(f"Configuración: n_requests={n_requests}, zipf_s={zipf_s}")
    print("Cargando datos...")
    data = load_data(data_path)
    print(f"Datos cargados: {len(data)} edificaciones en las 5 zonas.")

    distributions = ["uniform", "zipf"]
    policies = ["allkeys-lru", "allkeys-lfu"]
    cache_sizes = [2, 10, 50, 200, 500]
    ttls = [15, 60, 300]

    results = []
    run_id = 1

    total_runs = len(distributions) * len(policies) * len(cache_sizes) * len(ttls)
    print(f"Total de experimentos: {total_runs}\n")

    for dist in distributions:
        for policy in policies:
            for size in cache_sizes:
                for ttl in ttls:
                    size_label = f"{int(size)}MB"
                    print(f"RUN {run_id}/{total_runs} | {dist} | {policy} | {size_label} | TTL={ttl}s")

                    summary = run_experiment(
                        dist, policy, size, ttl, data, run_id, n_requests, zipf_s
                    )

                    print(f"  hit_rate={summary['hit_rate']:.2f}  throughput={summary['throughput']:.1f} req/s")

                    results.append(summary)
                    run_id += 1

    save_results(results)

    import plot_results  # noqa: F401


def save_results(results):
    """Guarda todos los resultados en CSV para análisis posterior."""
    os.makedirs("../results", exist_ok=True)
    keys = results[0].keys()

    with open("../results/results_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    print("\nResultados guardados en results/results_summary.csv")


if __name__ == "__main__":
    main()
