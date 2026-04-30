def q1_count(data, zone, confidence):
    """
    Q1: Cuenta el número de edificaciones en una zona con confianza >= confidence.
    Es la consulta más frecuente para estimar densidad de puntos de entrega.
    """
    return sum(1 for b in data if b["zone"] == zone and b["confidence"] >= confidence)


def q2_area(data, zone, confidence):
    """
    Q2: Calcula área promedio y área total de edificaciones en una zona.
    Útil para clasificar sectores según tipo de construcción (residencial vs comercial).
    """
    areas = [b["area"] for b in data if b["zone"] == zone and b["confidence"] >= confidence]

    if not areas:
        return {"avg_area": 0, "total_area": 0, "count": 0}

    return {
        "avg_area": sum(areas) / len(areas),
        "total_area": sum(areas),
        "count": len(areas)
    }


def q3_density(data, zone, confidence, zone_areas):
    """
    Q3: Calcula densidad de edificaciones por km² en una zona.
    Normaliza por el área del bounding box para comparar zonas de distinto tamaño.
    """
    count = q1_count(data, zone, confidence)
    area_km2 = zone_areas.get(zone, 1)
    if area_km2 == 0:
        return 0
    return count / area_km2


def q4_compare_density(data, zone_a, zone_b, confidence, zone_areas):
    """
    Q4: Compara la densidad de edificaciones entre dos zonas.
    Las empresas de reparto usan esta consulta para priorizar zonas de expansión.
    """
    density_a = q3_density(data, zone_a, confidence, zone_areas)
    density_b = q3_density(data, zone_b, confidence, zone_areas)

    if density_a > density_b:
        winner = zone_a
    elif density_b > density_a:
        winner = zone_b
    else:
        winner = "tie"

    return {
        "zone_a": zone_a, "density_a": density_a,
        "zone_b": zone_b, "density_b": density_b,
        "winner": winner
    }


def q5_confidence_distribution(data, zone, bins=5):
    """
    Q5: Calcula la distribución del score de confianza en intervalos uniformes [0,1].
    Permite evaluar la calidad del dato geoespacial antes de tomar decisiones operativas.
    """
    confidences = [b["confidence"] for b in data if b["zone"] == zone]

    if not confidences:
        return []

    step = 1 / bins
    distribution = []

    for i in range(bins):
        min_val = round(i * step, 2)
        max_val = round((i + 1) * step, 2)
        if i == bins - 1:
            count = sum(1 for c in confidences if min_val <= c <= max_val)
        else:
            count = sum(1 for c in confidences if min_val <= c < max_val)

        distribution.append({"bucket": i + 1, "min": min_val, "max": max_val, "count": count})

    return distribution


def execute_query(data, request, zone_areas):
    """Despacha la consulta al handler correspondiente según query_type (Q1-Q5)."""
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
        return q4_compare_density(data, zone, request["zone_b"], confidence, zone_areas)
    if query_type == "Q5":
        return q5_confidence_distribution(data, zone, request.get("bins", 5))

    return {"error": "Tipo de consulta no válido"}
