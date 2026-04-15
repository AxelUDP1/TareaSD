import json
import redis


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


def build_cache_key(request):
    """Construye una clave única para la consulta"""

    key = f"{request['query_type']}:{request['zone']}:{request.get('confidence', 0.0)}"

    if request["query_type"] == "Q4":
        key += f":{request['zone_b']}"

    if request["query_type"] == "Q5":
        key += f":bins={request.get('bins', 5)}"

    return key


def get_from_cache(key):
    """Busca una respuesta en Redis"""

    value = redis_client.get(key)

    if value is None:
        return None

    return json.loads(value)


def save_to_cache(key, value, ttl=60):
    """Guarda una respuesta en Redis con TTL"""

    redis_client.setex(
        key,
        ttl,
        json.dumps(value)
    )


def clear_cache():
    """Limpia toda la caché"""

    redis_client.flushdb()


def configure_cache(maxmemory_mb, policy):
    """Configura tamaño máximo y política de remoción"""

    redis_client.config_set("maxmemory", maxmemory_mb * 1024 * 1024)
    redis_client.config_set("maxmemory-policy", policy)


def get_cache_stats():
    """Obtiene estadísticas básicas de Redis"""

    info = redis_client.info()

    return {
        "keyspace_hits": info.get("keyspace_hits", 0),
        "keyspace_misses": info.get("keyspace_misses", 0),
        "evicted_keys": info.get("evicted_keys", 0),
        "used_memory": info.get("used_memory", 0)
    }