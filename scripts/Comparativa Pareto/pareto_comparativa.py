"""
Comparativa de frentes de Pareto: AMPL/Gurobi vs NSGA-II
Uso:
    python pareto_comparativa.py --ampl pareto_gurobiX.csv \\
                                  --nsga2 unique_solutions_X.csv \\
                                  --titulo "Instancia Grande"

    Solo NSGA-II (p. ej. instancia gigante):
    python pareto_comparativa.py --solo-nsga2 --nsga2 unique_solutions_....csv

    Generar las 5 comparativas en PNG (gigante = solo NSGA-II):
    python pareto_comparativa.py --batch --outdir ./figuras_pareto
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Backend no interactivo para --batch (servidores / sandbox sin display)
if "--batch" in sys.argv:
    import matplotlib

    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


# ── Dominancia ──────────────────────────────────────────────────────────────

def calcular_dominancia(df: pd.DataFrame) -> pd.Series:
    """Devuelve una Serie booleana: True = dominado."""
    pts = df[["Cost", "Time"]].values
    n = len(pts)
    dominado = np.zeros(n, dtype=bool)
    for i in range(n):
        if dominado[i]:
            continue
        for j in range(n):
            if i == j or dominado[j]:
                continue
            # j domina a i si es <= en ambos y < en al menos uno
            if pts[j, 0] <= pts[i, 0] and pts[j, 1] <= pts[i, 1]:
                if pts[j, 0] < pts[i, 0] or pts[j, 1] < pts[i, 1]:
                    dominado[i] = True
                    break
    return pd.Series(dominado, index=df.index)


# ── Carga de datos ───────────────────────────────────────────────────────────

def cargar_ampl(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = ["F1", "F2", "ExecTime"]
    return df.sort_values("F1").reset_index(drop=True)


def cargar_nsga2(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    pts = df[["Cost", "Time"]].drop_duplicates().reset_index(drop=True)
    pts["dominado"] = calcular_dominancia(pts)
    return pts


# ── Gráfico ──────────────────────────────────────────────────────────────────

def graficar(
    ampl: pd.DataFrame | None,
    nsga2: pd.DataFrame,
    titulo: str,
    salida: str | None,
) -> None:

    nd = nsga2[~nsga2["dominado"]].sort_values("Cost")
    dom = nsga2[nsga2["dominado"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    # Dominados (fondo)
    ax.scatter(
        dom["Cost"],
        dom["Time"],
        color="#E24B4A",
        alpha=0.35,
        s=12,
        zorder=1,
        label=f"NSGA-II dominado ({len(dom)})",
    )

    # No dominados NSGA-II
    n_pts = min(len(nd), 2000)  # limitar puntos en frentes muy densos
    step = max(1, len(nd) // n_pts)
    nd_plot = nd.iloc[::step]
    ax.plot(
        nd_plot["Cost"],
        nd_plot["Time"],
        color="#1D9E75",
        linewidth=1.4,
        zorder=3,
    )
    ax.scatter(
        nd_plot["Cost"],
        nd_plot["Time"],
        color="#1D9E75",
        s=14,
        zorder=4,
        label=f"NSGA-II no dominado ({len(nd)})",
    )

    # Frente AMPL/Gurobi (opcional)
    if ampl is not None and len(ampl) > 0:
        ax.plot(
            ampl["F1"],
            ampl["F2"],
            color="#185FA5",
            linewidth=1.6,
            linestyle="--",
            zorder=5,
        )
        ax.scatter(
            ampl["F1"],
            ampl["F2"],
            color="#185FA5",
            s=55,
            zorder=6,
            label=f"AMPL/Gurobi ({len(ampl)})",
        )

    # Ejes y leyenda
    ax.set_xlabel("Costo (F1)", fontsize=12)
    ax.set_ylabel("Tiempo (F2)", fontsize=12)
    ax.set_title(titulo, fontsize=13, pad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{int(y):,}"))
    ax.grid(True, color="gray", alpha=0.15, linewidth=0.6)
    ax.legend(fontsize=10, framealpha=0.9)

    # Estadísticas en recuadro
    total = len(nsga2)
    pct_nd = 100 * len(nd) / total if total else 0
    txt = (
        f"Total NSGA-II: {total:,}\n"
        f"No dominados:  {len(nd):,}  ({pct_nd:.1f}%)\n"
        f"Dominados:     {len(dom):,}  ({100-pct_nd:.1f}%)"
    )
    if ampl is not None and len(ampl) > 0:
        txt = f"AMPL/Gurobi: {len(ampl)} puntos\n" + txt
    ax.text(
        0.4,
        0.97,
        txt,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor="white",
            edgecolor="gray",
            alpha=0.8,
        ),
    )

    plt.tight_layout()

    if salida:
        plt.savefig(salida, dpi=150, bbox_inches="tight")
        print(f"Guardado en: {salida}")
    else:
        plt.show()
    plt.close(fig)


# ── Lote instancias ─────────────────────────────────────────────────────

def _dir_script() -> Path:
    return Path(__file__).resolve().parent


# (clave_archivo, csv_gurobi o None, csv_nsga2, título)
BATCH_SPECS: list[tuple[str, str | None, str, str]] = [
    (
        "basica",
        "pareto_gurobiBasica.csv",
        #"unique_solutions_instancia_basica_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "unique_solutions_instancia_basica_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "Instancia básica — Pareto AMPL/Gurobi vs NSGA-II",
    ),
    (
        "intermedia",
        "pareto_gurobiIntermedio.csv",
        #"unique_solutions_instancia_intermedia_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "unique_solutions_instancia_intermedia_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "Instancia intermedia — Pareto AMPL/Gurobi vs NSGA-II",
    ),
    (
        "intermedia_grande",
        "pareto_gurobiIntermedio_grande.csv",
        #"unique_solutions_instancia_intermedia_grande_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "unique_solutions_instancia_intermedia_grande_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "Instancia intermedia grande — Pareto AMPL/Gurobi vs NSGA-II",
    ),
    (
        "grande",
        "pareto_gurobiGrande.csv",
        #"unique_solutions_instancia_grande_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "unique_solutions_instancia_grande_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "Instancia grande — Pareto AMPL/Gurobi vs NSGA-II",
    ),
    (
        "gigante",
        None,
        #"unique_solutions_instancia_gigante_pop1000_ngen4000_pc0_9_pm0_01_div0_pres0.csv",
        "unique_solutions_instancia_gigante_pop1000_ngen4000_pc0_9_pm0_01_div1_pres1.csv",
        "Instancia gigante — frente NSGA-II",
    )
]


def ejecutar_batch(outdir: Path) -> None:
    base = _dir_script()
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    for clave, gurobi_name, nsga_name, titulo in BATCH_SPECS:
        path_nsga = base / nsga_name
        if not path_nsga.is_file():
            raise FileNotFoundError(f"No existe CSV NSGA-II: {path_nsga}")

        ampl_df: pd.DataFrame | None = None
        if gurobi_name is not None:
            path_gurobi = base / gurobi_name
            if not path_gurobi.is_file():
                raise FileNotFoundError(f"No existe CSV Gurobi: {path_gurobi}")
            ampl_df = cargar_ampl(str(path_gurobi))

        print(f"\n--- {clave} ---")
        nsga2 = cargar_nsga2(str(path_nsga))
        nd = nsga2[~nsga2["dominado"]]
        dom = nsga2[nsga2["dominado"]]
        if ampl_df is not None:
            print(f"  AMPL:              {len(ampl_df)} puntos")
        else:
            print("  AMPL:              (no incluido — solo NSGA-II)")
        print(f"  NSGA-II total:     {len(nsga2)} puntos únicos")
        print(f"  NSGA-II no domin.: {len(nd)}")
        print(f"  NSGA-II dominados: {len(dom)}")

        salida = outdir / f"pareto_{clave}.png"
        print(f"Generando gráfico → {salida}")
        graficar(ampl_df, nsga2, titulo=titulo, salida=str(salida))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara frentes de Pareto de AMPL vs NSGA-II"
    )
    parser.add_argument(
        "--ampl",
        default=None,
        help="CSV del frente de Pareto de AMPL/Gurobi (omitir con --solo-nsga2)",
    )
    parser.add_argument("--nsga2", default=None, help="CSV soluciones únicas NSGA-II")
    parser.add_argument(
        "--titulo", default="Comparativa Pareto", help="Título del gráfico"
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta de salida (ej: grafico.png). Sin --salida, se muestra en pantalla.",
    )
    parser.add_argument(
        "--solo-nsga2",
        action="store_true",
        help="Solo frente NSGA-II (sin AMPL/Gurobi)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Generar los 5 PNG (gigante solo NSGA-II) en --outdir",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Directorio de salida para --batch (por defecto: carpeta del script/figuras_pareto)",
    )
    args = parser.parse_args()

    if args.batch:
        out = args.outdir if args.outdir is not None else _dir_script() / "figuras_pareto"
        ejecutar_batch(out)
        return

    if args.nsga2 is None:
        parser.error("Indica --nsga2 o usa --batch.")

    if not args.solo_nsga2:
        if args.ampl is None:
            parser.error("Indica --ampl o usa --solo-nsga2.")
        ampl = cargar_ampl(args.ampl)
    else:
        ampl = None

    print("Cargando datos...")
    nsga2 = cargar_nsga2(args.nsga2)

    nd = nsga2[~nsga2["dominado"]]
    dom = nsga2[nsga2["dominado"]]
    if ampl is not None:
        print(f"  AMPL:              {len(ampl)} puntos")
    else:
        print("  AMPL:              (solo NSGA-II)")
    print(f"  NSGA-II total:     {len(nsga2)} puntos únicos")
    print(f"  NSGA-II no domin.: {len(nd)}")
    print(f"  NSGA-II dominados: {len(dom)}")

    print("Generando gráfico...")
    graficar(ampl, nsga2, titulo=args.titulo, salida=args.salida)


if __name__ == "__main__":
    main()