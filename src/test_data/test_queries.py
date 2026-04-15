from query_processor import (
    q1_count,
    q2_area,
    q3_density,
    q4_compare_density,
    q5_confidence_distribution
)

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

print("Q1 result:", q1_count(sample_data, "Z1", 0.5))
print("Q2 result:", q2_area(sample_data, "Z1", 0.5))
print("Q3 result:", q3_density(sample_data, "Z1", 0.5, zone_areas))
print("Q4 result:", q4_compare_density(sample_data, "Z1", "Z2", 0.5, zone_areas))
print("Q5 result:", q5_confidence_distribution(sample_data, "Z1", bins=5))