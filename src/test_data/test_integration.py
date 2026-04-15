from cache import build_cache_key, get_from_cache, save_to_cache, clear_cache
from query_processor import execute_query

sample_data = [
    {"zone": "Z1", "confidence": 0.8, "area": 100},
    {"zone": "Z1", "confidence": 0.6, "area": 120},
    {"zone": "Z1", "confidence": 0.3, "area": 90},
    {"zone": "Z2", "confidence": 0.9, "area": 200},
    {"zone": "Z2", "confidence": 0.7, "area": 150},
]

zone_areas = {
    "Z1": 2.0,
    "Z2": 4.0
}

request = {
    "query_type": "Q1",
    "zone": "Z1",
    "confidence": 0.5
}

clear_cache()

key = build_cache_key(request)

cached_result = get_from_cache(key)
print("Primer intento:", cached_result)

if cached_result is None:
    result = execute_query(sample_data, request, zone_areas)
    save_to_cache(key, result)
    print("Calculado y guardado:", result)

cached_result = get_from_cache(key)
print("Segundo intento:", cached_result)