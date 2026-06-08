"""
plot_nsga2_heatmaps.py
----------------------
Genera mapas de calor de Score, Hypervolume y un indicador combinado
por configuracion (Popsize x Ngen).
Las combinaciones faltantes se pintan en gris.

Uso:
    python plot_nsga2_heatmaps.py
    python plot_nsga2_heatmaps.py --csv ruta/al/archivo.csv
    python plot_nsga2_heatmaps.py --outdir resultados
    python plot_nsga2_heatmaps.py --annot
    python plot_nsga2_heatmaps.py --w-score 0.7 --w-hv 0.3
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def find_csv() -> str:
    """Busca un CSV por patrones conocidos y fallback general."""
    patterns = [
        "instancia_gigante_mixto_popsize_ngen_*.csv",
        "*.csv",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    sys.exit("No se encontro ningun CSV. Usa --csv para indicar la ruta.")


def load_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    required = {"Popsize", "Ngen", "Score", "Hypervolume"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"Faltan columnas requeridas en el CSV: {sorted(missing)}")
    return df


def build_matrix(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    pops = sorted(df["Popsize"].unique())
    ngens = sorted(df["Ngen"].unique())

    matrix = (
        df.pivot_table(index="Popsize", columns="Ngen", values=metric, aggfunc="mean")
        .reindex(index=pops, columns=ngens)
    )
    return matrix


def minmax_normalize(matrix: pd.DataFrame) -> pd.DataFrame:
    """Normaliza una matriz a [0, 1], preservando NaN."""
    min_val = np.nanmin(matrix.to_numpy(dtype=float))
    max_val = np.nanmax(matrix.to_numpy(dtype=float))
    if np.isclose(max_val, min_val):
        return matrix * 0.0
    return (matrix - min_val) / (max_val - min_val)


def plot_heatmap(
    matrix: pd.DataFrame,
    metric_label: str,
    outpath: str,
    cmap_name: str = "viridis",
    annot: bool = False,
):
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="#bdbdbd")  # gris para configuraciones faltantes (NaN)

    data = matrix.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(13, 7))
    im = ax.imshow(data, aspect="auto", cmap=cmap, interpolation="nearest")

    ax.set_title(f"Mapa de calor de {metric_label} por Popsize y Ngen", fontsize=13, pad=10)
    ax.set_xlabel("Ngen")
    ax.set_ylabel("Popsize")

    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels([str(x) for x in matrix.columns], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels([str(y) for y in matrix.index])

    if annot:
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = data[i, j]
                if np.isnan(value):
                    continue
                ax.text(j, i, f"{value:.3f}", ha="center", va="center", fontsize=7, color="white")

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(metric_label)

    plt.tight_layout()
    fig.savefig(outpath, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Genera heatmaps de Score, Hypervolume y combinado"
    )
    parser.add_argument("--csv", default=None, help="Ruta al archivo CSV")
    parser.add_argument("--outdir", default=".", help="Directorio de salida")
    parser.add_argument("--cmap", default="coolwarm", help="Colormap base")
    parser.add_argument("--annot", action="store_true", help="Mostrar valores en cada celda")
    parser.add_argument(
        "--w-score",
        type=float,
        default=0.5,
        help="Peso del Score para el mapa combinado (default: 0.5)",
    )
    parser.add_argument(
        "--w-hv",
        type=float,
        default=0.5,
        help="Peso del Hypervolume para el mapa combinado (default: 0.5)",
    )
    args = parser.parse_args()

    csv_path = args.csv or find_csv()
    print(f"Leyendo: {csv_path}")
    df = load_csv(csv_path)
    os.makedirs(args.outdir, exist_ok=True)

    score_matrix = build_matrix(df, "Score")
    hv_matrix = build_matrix(df, "Hypervolume")
    score_norm = minmax_normalize(score_matrix)
    hv_norm = minmax_normalize(hv_matrix)

    weight_sum = args.w_score + args.w_hv
    if np.isclose(weight_sum, 0.0):
        sys.exit("La suma de pesos no puede ser 0. Ajusta --w-score y --w-hv.")

    w_score = args.w_score / weight_sum
    w_hv = args.w_hv / weight_sum
    combined_matrix = (score_norm * w_score) + (hv_norm * w_hv)

    score_out = os.path.join(args.outdir, "nsga2_score_heatmap.png")
    hv_out = os.path.join(args.outdir, "nsga2_hypervolume_heatmap.png")
    combined_out = os.path.join(args.outdir, "nsga2_combined_heatmap.png")

    plot_heatmap(score_matrix, "Score", score_out, cmap_name=args.cmap, annot=args.annot)
    plot_heatmap(hv_matrix, "Hypervolume", hv_out, cmap_name=args.cmap, annot=args.annot)
    plot_heatmap(
        combined_matrix,
        f"Combinado (Score {w_score:.2f} + HV {w_hv:.2f})",
        combined_out,
        cmap_name=args.cmap,
        annot=args.annot,
    )

    print(f"Guardado -> {score_out}")
    print(f"Guardado -> {hv_out}")
    print(f"Guardado -> {combined_out}")
    print("Listo.")


if __name__ == "__main__":
    main()
