import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sys
import os

# ── Configuración de archivos ──────────────────────────────────────────────────
FILES = {
    "Sin Diversidad/Preservación (div=0, pres=0)": (
        "unique_solutions_instancia_basica_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "#E74C3C",   # rojo
        "hollow",
    ),
    "Con Diversidad/Preservación (div=1, pres=1)": (
        "unique_solutions_instancia_basica_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "#2980B9",   # azul
        "solid",
    ),
}

# ── Función de dominancia de Pareto ───────────────────────────────────────────
def pareto_front(costs: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Devuelve máscara booleana con las soluciones no dominadas (minimización en ambos objetivos)."""
    n = len(costs)
    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # j domina a i si es mejor o igual en ambos objetivos y estrictamente mejor en al menos uno
            if (costs[j] <= costs[i] and times[j] <= times[i] and
                    (costs[j] < costs[i] or times[j] < times[i])):
                dominated[i] = True
                break
    return ~dominated


# ── Graficar ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 6))

for label, (filename, color, style) in FILES.items():
    # Buscar el archivo en el directorio actual o en uploads
    for search_path in [".", "/mnt/user-data/uploads"]:
        full_path = os.path.join(search_path, filename)
        if os.path.isfile(full_path):
            break
    else:
        print(f"[ADVERTENCIA] No se encontró: {filename}")
        continue

    df = pd.read_csv(full_path)

    costs = df["Cost"].values
    times = df["Time"].values

    mask = pareto_front(costs, times)
    pf_cost = costs[mask]
    pf_time = times[mask]

    # Ordenar por costo para que la línea se vea bien
    order = np.argsort(pf_cost)
    pf_cost = pf_cost[order]
    pf_time = pf_time[order]

    # Scatter + línea escalonada (step)
    ax.step(pf_cost, pf_time, where="post", color=color, linewidth=1.4,
            linestyle="--", alpha=0.7)
    if style == "hollow":
        ax.scatter(pf_cost, pf_time, s=70, zorder=5,
                   facecolors="none", edgecolors=color, linewidths=1.8,
                   label=f"{label}  (n={mask.sum()})")
    else:
        ax.scatter(pf_cost, pf_time, color=color, s=60, zorder=4,
                   edgecolors="white", linewidths=0.6,
                   label=f"{label}  (n={mask.sum()})")

# ── Estética ──────────────────────────────────────────────────────────────────
ax.set_xlabel("Costo", fontsize=12)
ax.set_ylabel("Tiempo de Makespan", fontsize=12)
ax.set_title("Comparación de Frentes de Pareto\nInstancia Básica — NSGA-II", fontsize=13, fontweight="bold")
ax.legend(fontsize=10, framealpha=0.9)
ax.grid(True, linestyle="--", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()

output_path = "pareto_fronts_comparison.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"Gráfico guardado en: {output_path}")
plt.show()
