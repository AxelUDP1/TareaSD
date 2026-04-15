def q1_count(data, zone, confidence):
    """Cuenta edificios en una zona con confianza mínima"""

    count = 0

    for building in data:
        if building["zone"] == zone and building["confidence"] >= confidence:
            count += 1

    return count


def q2_area(data, zone, confidence):
    """Calcula área promedio y área total en una zona"""

    areas = []

    for building in data:
        if building["zone"] == zone and building["confidence"] >= confidence:
            areas.append(building["area"])

    if len(areas) == 0:
        return {
            "avg_area": 0,
            "total_area": 0,
            "count": 0
        }

    return {
        "avg_area": sum(areas) / len(areas),
        "total_area": sum(areas),
        "count": len(areas)
    }

def q3_density(data, zone, confidence, zone_areas):
    """Calcula densidad de edificios por km² en una zona"""

    count = q1_count(data, zone, confidence)
    area_km2 = zone_areas.get(zone, 1)

    if area_km2 == 0:
        return 0

    return count / area_km2


def q4_compare_density(data, zone_a, zone_b, confidence, zone_areas):
    """Compara la densidad de edificios entre dos zonas"""

    density_a = q3_density(data, zone_a, confidence, zone_areas)
    density_b = q3_density(data, zone_b, confidence, zone_areas)

    if density_a > density_b:
        winner = zone_a
    elif density_b > density_a:
        winner = zone_b
    else:
        winner = "Empate"

    return {
        "zone_a": zone_a,
        "density_a": density_a,
        "zone_b": zone_b,
        "density_b": density_b,
        "winner": winner
    }


def q5_confidence_distribution(data, zone, bins=5):
    """Calcula la distribución de confianza en intervalos"""

    confidences = []

    for building in data:
        if building["zone"] == zone:
            confidences.append(building["confidence"])

    if len(confidences) == 0:
        return []

    step = 1 / bins
    distribution = []

    for i in range(bins):
        min_value = round(i * step, 2)
        max_value = round((i + 1) * step, 2)

        count = 0
        for confidence in confidences:
            if i == bins - 1:
                if min_value <= confidence <= max_value:
                    count += 1
            else:
                if min_value <= confidence < max_value:
                    count += 1

        distribution.append({
            "bucket": i + 1,
            "min": min_value,
            "max": max_value,
            "count": count
        })

    return distribution

def execute_query(data, request, zone_areas):
    """Ejecuta la consulta según su tipo"""

    query_type = request["query_type"]
    zone = request["zone"]
    confidence = request.get("confidence", 0.0)

    if query_type == "Q1":
        return q1_count(data, zone, confidence)

    if query_type == "Q2":
        return q2_area(data, zone, confidence)

    if query_type == "Q3":
        return q3_density(data, zone, confidence, zone_areas)

    if query_type == "Q4":
        zone_b = request["zone_b"]
        return q4_compare_density(data, zone, zone_b, confidence, zone_areas)

    if query_type == "Q5":
        bins = request.get("bins", 5)
        return q5_confidence_distribution(data, zone, bins)

    return {"error": "Tipo de consulta no válido"}