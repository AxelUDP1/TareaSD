import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os

matplotlib.use("Agg")

OUTPUT_DIR = "../results"
df = pd.read_csv(f"{OUTPUT_DIR}/results_summary.csv")

df["policy"] = df["policy"].str.replace("allkeys-", "", regex=False)

# Orden correcto de tamaños (de menor a mayor) para los ejes
size_order = (
    df.drop_duplicates("cache_size_mb")
    .sort_values("cache_size_mb")["cache_size_label"]
    .tolist()
)


def save(fig, name):
    fig.savefig(f"{OUTPUT_DIR}/{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def label_mean_by_size(subset_df):
    """Devuelve (labels, values) ordenados por tamaño de caché."""
    grouped = subset_df.groupby("cache_size_label")["hit_rate"].mean()
    labels = [l for l in size_order if l in grouped.index]
    values = [grouped[l] for l in labels]
    return labels, values


# 1. Hit rate por distribución de tráfico
fig, ax = plt.subplots()
for dist in df["distribution"].unique():
    subset = df[df["distribution"] == dist]
    labels, values = label_mean_by_size(subset)
    ax.plot(labels, values, marker="o", label=dist)
ax.set_title("Hit Rate por Distribución de Tráfico")
ax.set_xlabel("Tamaño de Caché")
ax.set_ylabel("Hit Rate")
ax.legend()
ax.grid(True)
save(fig, "hit_rate_por_distribucion")

# 2. Hit rate por política de reemplazo
fig, ax = plt.subplots()
for policy in df["policy"].unique():
    subset = df[df["policy"] == policy]
    labels, values = label_mean_by_size(subset)
    ax.plot(labels, values, marker="o", label=policy)
ax.set_title("Hit Rate por Política de Reemplazo")
ax.set_xlabel("Tamaño de Caché")
ax.set_ylabel("Hit Rate")
ax.legend()
ax.grid(True)
save(fig, "hit_rate_por_politica")

# 3. Hit rate por tamaño de caché
fig, ax = plt.subplots()
means = df.groupby("cache_size_label")["hit_rate"].mean()
values = [means[l] for l in size_order if l in means.index]
ax.bar(size_order, values, color="steelblue")
ax.set_title("Hit Rate por Tamaño de Caché")
ax.set_xlabel("Tamaño de Caché")
ax.set_ylabel("Hit Rate promedio")
ax.set_ylim(0, 1)
ax.grid(axis="y")
save(fig, "hit_rate_por_tamano_cache")

# 4. Hit rate por TTL
fig, ax = plt.subplots()
for dist in df["distribution"].unique():
    subset = df[df["distribution"] == dist].groupby("ttl")["hit_rate"].mean()
    ax.plot(subset.index, subset.values, marker="o", label=dist)
ax.set_title("Hit Rate por TTL")
ax.set_xlabel("TTL (segundos)")
ax.set_ylabel("Hit Rate promedio")
ax.legend()
ax.grid(True)
save(fig, "hit_rate_por_ttl")

# 5. Latencia p50 y p95 por distribución
fig, ax = plt.subplots()
dists = list(df["distribution"].unique())
x = range(len(dists))
p50_means = [df[df["distribution"] == d]["latency_p50"].mean() * 1000 for d in dists]
p95_means = [df[df["distribution"] == d]["latency_p95"].mean() * 1000 for d in dists]
width = 0.35
ax.bar([i - width / 2 for i in x], p50_means, width, label="p50", color="steelblue")
ax.bar([i + width / 2 for i in x], p95_means, width, label="p95", color="salmon")
ax.set_title("Latencia p50 y p95 por Distribución")
ax.set_xlabel("Distribución")
ax.set_ylabel("Latencia (ms)")
ax.set_xticks(list(x))
ax.set_xticklabels(dists)
ax.legend()
ax.grid(axis="y")
save(fig, "latencia_p50_p95")

# 6. Throughput por distribución y política
fig, ax = plt.subplots()
for policy in df["policy"].unique():
    subset = df[df["policy"] == policy].groupby("distribution")["throughput"].mean()
    ax.bar(
        [f"{d}\n{policy}" for d in subset.index],
        subset.values,
        label=policy
    )
ax.set_title("Throughput por Distribución y Política")
ax.set_xlabel("Distribución / Política")
ax.set_ylabel("Consultas por segundo")
ax.grid(axis="y")
save(fig, "throughput_por_distribucion_politica")

# 7. Tasa de evicción por tamaño de caché y política
fig, ax = plt.subplots()
for policy in df["policy"].unique():
    subset = df[df["policy"] == policy].groupby("cache_size_label")["eviction_rate"].mean()
    labels = [l for l in size_order if l in subset.index]
    values = [subset[l] for l in labels]
    ax.plot(labels, values, marker="o", label=policy)
ax.set_title("Tasa de Evicción por Tamaño de Caché y Política")
ax.set_xlabel("Tamaño de Caché")
ax.set_ylabel("Evictions por cada 100 requests")
ax.legend()
ax.grid(True)
save(fig, "tasa_eviccion")

# 8. Eficiencia de caché por distribución y política
fig, ax = plt.subplots()
groups = df.groupby(["distribution", "policy"])["cache_efficiency"].mean()
labels = [f"{d}\n{p}" for d, p in groups.index]
ax.bar(labels, groups.values, color="mediumseagreen")
ax.set_title("Eficiencia de Caché por Distribución y Política")
ax.set_xlabel("Distribución / Política")
ax.set_ylabel("Eficiencia de Caché")
ax.grid(axis="y")
save(fig, "eficiencia_cache")

# 9. Miss rate por distribución
fig, ax = plt.subplots()
for dist in df["distribution"].unique():
    subset = df[df["distribution"] == dist]
    grouped = subset.groupby("cache_size_label")["miss_rate"].mean()
    labels = [l for l in size_order if l in grouped.index]
    values = [grouped[l] for l in labels]
    ax.plot(labels, values, marker="o", label=dist)
ax.set_title("Miss Rate por Distribución de Tráfico")
ax.set_xlabel("Tamaño de Caché")
ax.set_ylabel("Miss Rate")
ax.legend()
ax.grid(True)
save(fig, "miss_rate_por_distribucion")

print(f"9 gráficos generados en {os.path.abspath(OUTPUT_DIR)}/")
