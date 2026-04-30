import random
import numpy as np

QUERY_TYPES = ["Q1", "Q2", "Q3", "Q4", "Q5"]
ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5"]


def _build_request(query_type, zone):
    """Construye un request con sus parámetros según el tipo de consulta."""
    confidence = round(random.uniform(0.0, 1.0), 1)
    request = {
        "query_type": query_type,
        "zone": zone,
        "confidence": confidence
    }
    if query_type == "Q4":
        request["zone_b"] = random.choice(ZONES)
    if query_type == "Q5":
        request["bins"] = random.choice([5, 10])
    return request


def generate_uniform_requests(n=500):
    """
    Genera n consultas con distribución uniforme sobre zonas y tipos de consulta.
    Cada zona y tipo de consulta tiene igual probabilidad de ser seleccionado.
    """
    requests = []
    for _ in range(n):
        query_type = random.choice(QUERY_TYPES)
        zone = random.choice(ZONES)
        requests.append(_build_request(query_type, zone))
    return requests


def generate_zipf_requests(n=500, s=2.0):
    """
    Genera n consultas siguiendo una distribución Zipf sobre las zonas.
    El parámetro s controla el sesgo: mayor s = más concentración en pocas zonas.
    Simula el comportamiento real donde ciertas zonas son consultadas con mucha
    más frecuencia (ej. centros comerciales o zonas urbanas densas).
    """
    requests = []
    indices = np.random.zipf(s, n)
    for i in indices:
        zone = ZONES[i % len(ZONES)]
        query_type = random.choice(QUERY_TYPES)
        requests.append(_build_request(query_type, zone))
    return requests
