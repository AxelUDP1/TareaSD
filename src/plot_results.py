import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../results/results_summary.csv")

# Comparar hit rate por distribución
plt.figure()
for dist in df["distribution"].unique():
    subset = df[df["distribution"] == dist]
    plt.plot(subset["run_id"], subset["hit_rate"], label=dist)

plt.title("Hit Rate por distribución")
plt.xlabel("Run")
plt.ylabel("Hit Rate")
plt.legend()
plt.savefig("../results/hit_rate.png")

# Comparar políticas
plt.figure()
for policy in df["policy"].unique():
    subset = df[df["policy"] == policy]
    plt.plot(subset["run_id"], subset["hit_rate"], label=policy)

plt.title("Hit Rate por política")
plt.xlabel("Run")
plt.ylabel("Hit Rate")
plt.legend()
plt.savefig("../results/policy_comparison.png")

print("Gráficos generados")