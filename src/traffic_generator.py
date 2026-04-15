import random

# Tipos de consultas disponibles
QUERY_TYPES = ["Q1", "Q2", "Q3", "Q4", "Q5"]

# Zonas disponibles
ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5"]


def generate_request():

    query_type = random.choice(QUERY_TYPES)
    zone = random.choice(ZONES)
    confidence = round(random.uniform(0.0, 1.0), 1)

    request = {
        "query_type": query_type,
        "zone": zone,
        "confidence": confidence
    }

    # Q4 necesita comparar dos zonas
    if query_type == "Q4":
        zone_b = random.choice(ZONES)
        request["zone_b"] = zone_b

    return request


def generate_uniform_requests(n):


    requests = []

    for _ in range(n):
        request = generate_request()
        requests.append(request)

    return requests

import numpy as np

def generate_zipf_requests(n, s=2):


    requests = []

    # Genera índices con distribución Zipf
    indices = np.random.zipf(s, n)

    for i in indices:
        # Mapear índice a zona para forzar repetición
        zone = ZONES[i % len(ZONES)]

        query_type = random.choice(QUERY_TYPES)
        confidence = round(random.uniform(0.0, 1.0), 1)

        request = {
            "query_type": query_type,
            "zone": zone,
            "confidence": confidence
        }

        if query_type == "Q4":
            request["zone_b"] = random.choice(ZONES)

        requests.append(request)

    return requests