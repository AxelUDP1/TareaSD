from cache import build_cache_key, get_from_cache, save_to_cache, clear_cache, configure_cache, get_cache_stats

request = {
    "query_type": "Q1",
    "zone": "Z1",
    "confidence": 0.5
}

clear_cache()
configure_cache(50, "allkeys-lru")

key = build_cache_key(request)

print("Antes:", get_from_cache(key))

save_to_cache(key, 123, ttl=60)

print("Después:", get_from_cache(key))
print("Stats:", get_cache_stats())