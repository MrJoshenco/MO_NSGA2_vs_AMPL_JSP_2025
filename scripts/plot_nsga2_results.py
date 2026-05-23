"""
plot_nsga2_results.py
---------------------
Regenera los gráficos de Score e Hypervolumen a partir del CSV de resultados
del NSGA-2 custom (instancia_grande_mixto_popsize_ngen_*.csv).

Uso:
    python plot_nsga2_results.py                          # usa el CSV del mismo directorio
    python plot_nsga2_results.py --csv ruta/al/archivo.csv
    python plot_nsga2_results.py --metric score           # solo Score
    python plot_nsga2_results.py --metric hv              # solo Hypervolumen
    python plot_nsga2_results.py --pops 200,800,1600      # filtrar popsizes
    python plot_nsga2_results.py --outdir resultados/     # carpeta de salida

Dependencias:
    pip install pandas matplotlib
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd


# ──────────────────────────────────────────────
# Paleta de colores (una por Popsize)
# ──────────────────────────────────────────────
PALETTE = [
    "#378ADD", "#1D9E75", "#D85A30", "#D4537E", "#7F77DD",
    "#BA7517", "#A32D2D", "#1a8c8c", "#8c8c1a", "#4a1a8c",
    "#8c4a1a", "#1a8c4a", "#4a8c1a", "#8c1a4a", "#1a4a8c",
]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df


def find_csv() -> str:
    """Busca el CSV en el directorio actual si no se especifica."""
    matches = glob.glob("instancia_grande_mixto_popsize_ngen_*.csv")
    if matches:
        return matches[0]
    matches = glob.glob("*.csv")
    if matches:
        return matches[0]
    sys.exit("No se encontró ningún CSV. Usa --csv para indicar la ruta.")


def plot_metric(
    df: pd.DataFrame,
    col: str,
    ylabel: str,
    title: str,
    pops: list[int],
    outpath: str,
    threshold: float | None = None,
):
    fig, ax = plt.subplots(figsize=(12, 5.5))

    for idx, pop in enumerate(pops):
        subset = df[df["Popsize"] == pop].sort_values("Ngen")
        color = PALETTE[idx % len(PALETTE)]
        ax.plot(
            subset["Ngen"],
            subset[col],
            label=f"Pop {pop}",
            color=color,
            linewidth=1.6,
            marker="o",
            markersize=2.5,
            alpha=0.9,
        )

    if threshold is not None:
        ax.axhline(threshold, color="#888", linestyle="--", linewidth=1, alpha=0.7,
                   label=f"Umbral {threshold}")

    ax.set_xlabel("Ngen (generaciones)", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="500", pad=12)
    ax.xaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.3, alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    legend = ax.legend(
        title="Popsize",
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        fontsize=9,
        title_fontsize=9,
        frameon=True,
        framealpha=0.9,
    )

    plt.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado → {outpath}")


def main():
    parser = argparse.ArgumentParser(description="Grafica Score e HV del NSGA-2")
    parser.add_argument("--csv", default=None, help="Ruta al archivo CSV")
    parser.add_argument(
        "--metric",
        choices=["score", "hv", "both"],
        default="both",
        help="Qué gráfico generar (score | hv | both)",
    )
    parser.add_argument(
        "--pops",
        default=None,
        help="Lista de Popsizes separados por coma, ej: 200,800,1600",
    )
    parser.add_argument(
        "--outdir",
        default=".",
        help="Directorio de salida para las imágenes",
    )
    args = parser.parse_args()

    csv_path = args.csv or find_csv()
    print(f"Leyendo: {csv_path}")
    df = load_csv(csv_path)

    # Popsizes disponibles
    all_pops = sorted(df["Popsize"].unique())

    if args.pops:
        selected_pops = [int(p.strip()) for p in args.pops.split(",")]
        missing = [p for p in selected_pops if p not in all_pops]
        if missing:
            print(f"  Advertencia: Popsizes no encontradas en el CSV: {missing}")
        selected_pops = [p for p in selected_pops if p in all_pops]
    else:
        # Por defecto muestra una selección representativa (máx 12 curvas)
        step = max(1, len(all_pops) // 12)
        selected_pops = all_pops[::step]

    print(f"Popsizes seleccionadas ({len(selected_pops)}): {selected_pops}")
    os.makedirs(args.outdir, exist_ok=True)

    # ── Score ──────────────────────────────────
    if args.metric in ("score", "both"):
        plot_metric(
            df,
            col="Score",
            ylabel="Score",
            title="Score por Ngen y Popsize — NSGA-2",
            pops=selected_pops,
            outpath=os.path.join(args.outdir, "nsga2_score.png"),
            threshold=1.0,
        )

    # ── Hypervolumen ───────────────────────────
    if args.metric in ("hv", "both"):
        plot_metric(
            df,
            col="Hypervolume",
            ylabel="Hypervolumen normalizado",
            title="Hypervolumen por Ngen y Popsize — NSGA-2",
            pops=selected_pops,
            outpath=os.path.join(args.outdir, "nsga2_hypervolume.png"),
            threshold=1.0,
        )

    print("\nListo.")


if __name__ == "__main__":
    main()