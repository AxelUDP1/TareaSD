import json
import os
import redis


redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True
)


def build_cache_key(request):
    """
    Construye la clave de caché según el formato definido en el enunciado.
    Formato por tipo:
      Q1 -> count:{zona}:conf={confidence}
      Q2 -> area:{zona}:conf={confidence}
      Q3 -> density:{zona}:conf={confidence}
      Q4 -> compare:density:{zona_a}:{zona_b}:conf={confidence}
      Q5 -> confidence_dist:{zona}:bins={bins}
    """
    query_type = request["query_type"]
    zone = request["zone"]
    confidence = request.get("confidence", 0.0)

    if query_type == "Q1":
        return f"count:{zone}:conf={confidence}"

    if query_type == "Q2":
        return f"area:{zone}:conf={confidence}"

    if query_type == "Q3":
        return f"density:{zone}:conf={confidence}"

    if query_type == "Q4":
        zone_b = request.get("zone_b", zone)
        return f"compare:density:{zone}:{zone_b}:conf={confidence}"

    if query_type == "Q5":
        bins = request.get("bins", 5)
        return f"confidence_dist:{zone}:bins={bins}"

    return f"{query_type}:{zone}:{confidence}"


def get_from_cache(key):
    """
    Busca una respuesta en Redis por su clave.
    Retorna el valor deserializado o None si no existe (cache miss).
    """
    value = redis_client.get(key)
    if value is None:
        return None
    return json.loads(value)


def save_to_cache(key, value, ttl=60):
    """
    Almacena una respuesta en Redis con tiempo de expiración (TTL).
    El TTL en segundos determina cuánto tiempo permanece válida la entrada.
    Si la caché está llena y no puede evictar, omite el almacenamiento.
    """
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except redis.exceptions.OutOfMemoryError:
        pass


def clear_cache():
    """Elimina todas las entradas de la base de datos Redis actual."""
    redis_client.flushdb()


def configure_cache(maxmemory_mb, policy):
    """
    Configura el tamaño máximo de memoria y la política de evicción de Redis.
    Políticas soportadas: allkeys-lru, allkeys-lfu, allkeys-random, noeviction.
    """
    redis_client.config_set("maxmemory", int(maxmemory_mb * 1024 * 1024))
    redis_client.config_set("maxmemory-policy", policy)


def get_cache_stats():
    """
    Obtiene estadísticas de rendimiento de Redis.
    Retorna hits, misses, evictions y uso de memoria actuales.
    """
    info = redis_client.info()
    return {
        "keyspace_hits": info.get("keyspace_hits", 0),
        "keyspace_misses": info.get("keyspace_misses", 0),
        "evicted_keys": info.get("evicted_keys", 0),
        "used_memory": info.get("used_memory", 0)
    }
