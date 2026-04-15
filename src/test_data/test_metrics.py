from metrics import MetricsCollector

metrics = MetricsCollector()

metrics.add_record("Q1", "hit", 0.002)
metrics.add_record("Q2", "miss", 0.020)
metrics.add_record("Q3", "hit", 0.001)
metrics.add_record("Q4", "miss", 0.030)
metrics.add_record("Q5", "hit", 0.003)

metrics.add_eviction(2)

summary = metrics.get_summary()

for key, value in summary.items():
    print(f"{key}: {value}")