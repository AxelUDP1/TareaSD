"""
Genera gráficos comparativos para los 7 escenarios de la Tarea 2.
Lee results/kafka_results_summary.csv y los JSON individuales por escenario.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "kafka")
OUT_DIR     = RESULTS_DIR

SCENARIO_LABELS = {
    "1_base":         "1. Base\nSíncrono",
    "2_kafka_1c":     "2. Kafka\n1 consumer",
    "3_kafka_4c":     "3. Kafka\n4 consumers",
    "4_falla":        "4. Falla\ntemporal",
    "5_reintentos":   "5. Reintentos",
    "6_spike":        "6. Spike\ntráfico",
    "7_recuperacion": "7. Recuperación",
}

COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52",
          "#8172B3", "#937860", "#DA8BC3"]


def _load_csv() -> pd.DataFrame:
    path = os.path.join(RESULTS_DIR, "kafka_results_summary.csv")
    if not os.path.exists(path):
        print(f"[plot] No se encontró {path}. Ejecuta main_kafka.py primero.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["label"] = df["scenario"].map(SCENARIO_LABELS).fillna(df["scenario"])
    return df


def _load_consumers_comparison() -> pd.DataFrame:
    """Lee los JSON individuales del escenario 3 (1, 2, 4 consumers)."""
    rows = []
    for n in [1, 2, 4]:
        path = os.path.join(RESULTS_DIR, f"kafka_metrics_3_kafka_{n}c.json")
        if os.path.exists(path):
            with open(path) as f:
                d = json.load(f)
            snaps = d.get("backlog_snapshots", [])
            peak_backlog = max((s[1] for s in snaps), default=0)
            rows.append({"consumers":    n,
                         "throughput":   d.get("throughput", 0),
                         "latency_p50":  d.get("latency_p50", 0),
                         "latency_p95":  d.get("latency_p95", 0),
                         "peak_backlog": peak_backlog})
    return pd.DataFrame(rows)


def _load_backlog_snapshots(scenario: str) -> list[tuple]:
    path = os.path.join(RESULTS_DIR, f"kafka_metrics_{scenario}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        d = json.load(f)
    return d.get("backlog_snapshots", [])


def _save(fig, name: str):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"[plot] {name}")


# ── Gráfico 1: Throughput por escenario ───────────────────────────────────────
def plot_throughput(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(df["label"], df["throughput"], color=COLORS[:len(df)])
    ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)
    ax.set_title("Throughput por escenario (req/s)")
    ax.set_ylabel("Consultas por segundo")
    ax.set_xlabel("Escenario")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "kafka_throughput_por_escenario.png")


# ── Gráfico 2: Latencia p50/p95 por escenario ─────────────────────────────────
def plot_latency(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(df))
    w = 0.35
    ax.bar([i - w/2 for i in x], df["latency_p50"] * 1000,
           width=w, label="p50", color="#4C72B0")
    ax.bar([i + w/2 for i in x], df["latency_p95"] * 1000,
           width=w, label="p95", color="#DD8452")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["label"])
    ax.set_title("Latencia p50 / p95 por escenario (ms)")
    ax.set_ylabel("Latencia (ms)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "kafka_latencia_por_escenario.png")


# ── Gráfico 3: Retry / Recovery / DLQ rates ───────────────────────────────────
def plot_retry_rates(df: pd.DataFrame):
    kafka_df = df[df["scenario"] != "1_base"].copy()
    if kafka_df.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(kafka_df))
    w = 0.28
    ax.bar([i - w for i in x], kafka_df["retry_rate"] * 100,
           width=w, label="Retry rate %", color="#C44E52")
    ax.bar([i       for i in x], kafka_df["recovery_rate"] * 100,
           width=w, label="Recovery rate %", color="#55A868")
    ax.bar([i + w   for i in x], kafka_df["dlq_rate"] * 100,
           width=w, label="DLQ rate %", color="#937860")
    ax.set_xticks(list(x))
    ax.set_xticklabels(kafka_df["label"])
    ax.set_title("Tasas de reintento, recuperación y DLQ (%)")
    ax.set_ylabel("%")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "kafka_retry_recovery_dlq.png")


# ── Gráfico 4: Escalamiento horizontal (escenario 3) ─────────────────────────
def plot_consumers_scaling(cdf: pd.DataFrame):
    if cdf.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].plot(cdf["consumers"], cdf["throughput"], "o-", color="#4C72B0", linewidth=2)
    axes[0].set_title("Throughput vs Nº de consumers")
    axes[0].set_xlabel("Consumers")
    axes[0].set_ylabel("req/s")
    axes[0].set_xticks(cdf["consumers"])
    axes[0].grid(alpha=0.3)

    axes[1].plot(cdf["consumers"], cdf["latency_p50"] * 1000,
                 "o-", label="p50", color="#4C72B0", linewidth=2)
    axes[1].plot(cdf["consumers"], cdf["latency_p95"] * 1000,
                 "s--", label="p95", color="#DD8452", linewidth=2)
    axes[1].set_title("Latencia vs Nº de consumers")
    axes[1].set_xlabel("Consumers")
    axes[1].set_ylabel("ms")
    axes[1].set_xticks(cdf["consumers"])
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    bars = axes[2].bar(cdf["consumers"].astype(str) + "c",
                       cdf["peak_backlog"], color="#55A868")
    axes[2].bar_label(bars, fmt="%d", padding=3, fontsize=9)
    axes[2].set_title("Backlog máximo vs Nº de consumers")
    axes[2].set_xlabel("Consumers")
    axes[2].set_ylabel("Mensajes pendientes (pico)")
    axes[2].grid(axis="y", alpha=0.3)

    fig.suptitle("Escenario 3: Escalamiento horizontal Kafka")
    _save(fig, "kafka_escalamiento_consumers.png")


# ── Gráfico 5: Evolución del backlog ─────────────────────────────────────────
def plot_backlog(scenarios: list[str]):
    fig, ax = plt.subplots(figsize=(12, 5))
    plotted = False
    for sc, color in zip(scenarios, COLORS):
        snaps = _load_backlog_snapshots(sc)
        if not snaps:
            continue
        t0 = snaps[0][0]
        times = [(s[0] - t0) for s in snaps]
        sizes = [s[1] for s in snaps]
        ax.plot(times, sizes, "o-", label=SCENARIO_LABELS.get(sc, sc),
                color=color, linewidth=2)
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_title("Evolución del backlog en Kafka")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Mensajes pendientes")
    ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, "kafka_backlog_evolucion.png")


# ── Gráfico 6: Síncrono vs Kafka – pérdida de consultas ──────────────────────
def plot_loss_comparison(df: pd.DataFrame):
    """Compara DLQ (pérdida) entre escenarios con fallos."""
    fault_scenarios = ["4_falla", "5_reintentos", "7_recuperacion"]
    fdf = df[df["scenario"].isin(fault_scenarios)].copy()
    if fdf.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(fdf["label"], fdf["dlq_rate"] * 100,
                  color=["#C44E52", "#DD8452", "#8172B3"])
    ax.bar_label(bars, fmt="%.2f%%", padding=3, fontsize=9)
    ax.set_title("Pérdida de consultas (DLQ rate) en escenarios con fallos")
    ax.set_ylabel("% de consultas enviadas a DLQ")
    ax.set_xlabel("Escenario")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "kafka_perdida_consultas.png")


# ── Gráfico 7: Destino de mensajes (procesados / reintentados / DLQ) ─────────
def plot_message_fate(df: pd.DataFrame):
    """Stacked bar: mensajes procesados exitosamente, reintentados y enviados a DLQ."""
    fault_scenarios = ["4_falla", "5_reintentos", "6_spike", "7_recuperacion"]
    fdf = df[df["scenario"].isin(fault_scenarios)].copy()
    if fdf.empty:
        return

    processed_vals, retried_vals, dlq_vals, labels = [], [], [], []
    for _, row in fdf.iterrows():
        sc = row["scenario"]
        path = os.path.join(RESULTS_DIR, f"kafka_metrics_{sc}.json")
        if os.path.exists(path):
            with open(path) as f:
                d = json.load(f)
            total   = d.get("total_processed", 0)
            retried = d.get("retried", 0)
            dlq     = d.get("dlq_count", 0)
        else:
            total, retried, dlq = int(row["total_processed"]), 0, 0
        processed_vals.append(total)
        retried_vals.append(retried)
        dlq_vals.append(dlq)
        labels.append(row["label"])

    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(labels))
    w = 0.55

    b1 = ax.bar(x, processed_vals, width=w, label="Procesados con éxito", color="#55A868")
    b2 = ax.bar(x, retried_vals, width=w, bottom=processed_vals,
                label="Reintentos acumulados", color="#DD8452")
    bottom2 = [p + r for p, r in zip(processed_vals, retried_vals)]
    b3 = ax.bar(x, dlq_vals, width=w, bottom=bottom2,
                label="DLQ (pérdida permanente)", color="#C44E52")

    ax.bar_label(b1, labels=[str(v) for v in processed_vals],
                 label_type="center", fontsize=8, color="white", fontweight="bold")
    ax.bar_label(b3, labels=[str(v) if v > 0 else "" for v in dlq_vals],
                 padding=3, fontsize=8)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_title("Destino de mensajes en escenarios con fallos")
    ax.set_ylabel("Número de mensajes")
    ax.set_xlabel("Escenario")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "kafka_recovery_drain_time.png")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    df = _load_csv()
    if df.empty:
        return

    cdf = _load_consumers_comparison()

    plot_throughput(df)
    plot_latency(df)
    plot_retry_rates(df)
    plot_consumers_scaling(cdf)
    plot_backlog(["4_falla", "5_reintentos", "6_spike", "7_recuperacion"])
    plot_loss_comparison(df)
    plot_message_fate(df)

    print("[plot] Gráficos Kafka generados en results/")


if __name__ == "__main__":
    main()
