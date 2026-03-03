#!/usr/bin/env python3
"""
Ejecuta cada instancia 50 veces con parámetros distintos.
En cada run: semilla aleatoria (registrada), una combinación de parámetros,
se guardan las métricas y al final se identifican y guardan los mejores parámetros + semilla.

Uso (desde la raíz del proyecto):
    python3 scripts/run_50_per_instance.py                    # Todas las instancias, 50 runs c/u
    python3 scripts/run_50_per_instance.py -n 3               # Solo las 3 instancias más grandes
    python3 scripts/run_50_per_instance.py --runs 30          # 30 runs por instancia en vez de 50
    python3 scripts/run_50_per_instance.py -o mi_experimento   # Carpeta de salida custom
"""

import csv
import os
import random
import subprocess
import sys
import time as time_module
from datetime import datetime
from pathlib import Path

# Importar lógica compartida con tune_parameters
import tune_parameters as tp

PROJECT_ROOT = Path(tp.PROJECT_ROOT)
EXECUTABLE = str(Path(tp.PROJECT_ROOT) / "build" / "nsga2r")
RESULTS_BASE = "results/50runs"
RUNS_PER_INSTANCE = 50

# Espacio de parámetros para muestrear 50 combinaciones distintas.
# NSGA-II requiere popsize >= 4 y múltiplo de 4 (ver src/nsga2r.c).
PARAM_GRID = {
    "popsize": [48, 100, 152, 200],
    "ngen": [100, 200, 300, 400, 500],
    "pcross": [0.7, 0.8, 0.9, 0.95],
    "pmut": [0.01, 0.05, 0.1, 0.15],
}


def generate_param_combinations(n, grid=None):
    """Genera n combinaciones distintas de parámetros (muestreo sin reemplazo del grid)."""
    grid = grid or PARAM_GRID
    import itertools
    names = list(grid.keys())
    values = list(grid.values())
    all_combos = list(itertools.product(*values))
    if len(all_combos) < n:
        # Con reemplazo si el grid es pequeño
        return [dict(zip(names, all_combos[random.randrange(len(all_combos))])) for _ in range(n)]
    return [dict(zip(names, c)) for c in random.sample(all_combos, n)]


def run_nsga2_with_timeout(seed, instance_path, popsize, ngen, pcross, pmut, timeout_sec=600):
    """Ejecuta NSGA-II con timeout configurable. Retorna (success, elapsed)."""
    cmd = [
        EXECUTABLE,
        f"{seed:.6f}",
        str(instance_path),
        str(popsize),
        str(ngen),
        "2",
        str(pcross),
        str(pmut),
    ]
    try:
        t0 = time_module.time()
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return result.returncode == 0, time_module.time() - t0
    except subprocess.TimeoutExpired:
        return False, float(timeout_sec)
    except Exception:
        return False, 0.0


def run_one(instance_path, run_index, param_combo, seed, timeout=600):
    """
    Ejecuta NSGA-II una vez. Devuelve dict con seed, params, metrics y exec_time,
    o None si falló.
    """
    success, elapsed = run_nsga2_with_timeout(
        seed=seed,
        instance_path=instance_path,
        popsize=param_combo["popsize"],
        ngen=param_combo["ngen"],
        pcross=param_combo["pcross"],
        pmut=param_combo["pmut"],
        timeout_sec=timeout,
    )
    if not success:
        return None
    solutions = tp.parse_pareto_results(instance_path)
    if not solutions:
        return None
    inst_info = tp.get_instance_info(instance_path)
    metrics = tp.calculate_metrics(solutions)
    if not metrics:
        return None
    score = tp.calculate_composite_score(metrics, inst_info)
    return {
        "run_index": run_index,
        "seed": seed,
        "popsize": param_combo["popsize"],
        "ngen": param_combo["ngen"],
        "pcross": param_combo["pcross"],
        "pmut": param_combo["pmut"],
        "best_cost": metrics["best_cost"],
        "best_time": metrics["best_time"],
        "worst_cost": metrics["worst_cost"],
        "worst_time": metrics["worst_time"],
        "avg_cost": metrics["avg_cost"],
        "avg_time": metrics["avg_time"],
        "total_solutions": metrics["total_solutions"],
        "unique_solutions": metrics["unique_solutions"],
        "spread_cost": metrics["spread_cost"],
        "spread_time": metrics["spread_time"],
        "hypervolume": metrics["hypervolume"],
        "score": score,
        "exec_time_sec": elapsed,
    }


def save_metrics_csv(results_dir, instance_name, runs_data, timestamp):
    """Guarda CSV con todas las métricas de los 50 runs."""
    path = results_dir / f"{instance_name}_50runs_metrics_{timestamp}.csv"
    if not runs_data:
        return path
    fieldnames = [
        "RunIndex", "Seed", "Popsize", "Ngen", "Pcross", "Pmut",
        "BestCost", "BestTime", "WorstCost", "WorstTime",
        "AvgCost", "AvgTime", "TotalSolutions", "UniqueSolutions",
        "SpreadCost", "SpreadTime", "Hypervolume", "Score", "ExecTimeSec",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in runs_data:
            row = {k: v for k, v in r.items() if k in fieldnames}
            row["Seed"] = f"{r['seed']:.6f}"
            w.writerow(row)
    return path


def save_best_csv(results_dir, instance_name, best_run, timestamp):
    """Guarda CSV con el mejor run: semilla y parámetros (y métricas)."""
    path = results_dir / f"{instance_name}_best_params_{timestamp}.csv"
    if not best_run:
        return path
    fieldnames = [
        "Seed", "Popsize", "Ngen", "Pcross", "Pmut",
        "BestCost", "BestTime", "UniqueSolutions", "Hypervolume", "Score", "ExecTimeSec",
    ]
    row = {
        "Seed": f"{best_run['seed']:.6f}",
        "Popsize": best_run["popsize"],
        "Ngen": best_run["ngen"],
        "Pcross": best_run["pcross"],
        "Pmut": best_run["pmut"],
        "BestCost": round(best_run["best_cost"], 2),
        "BestTime": round(best_run["best_time"], 2),
        "UniqueSolutions": best_run["unique_solutions"],
        "Hypervolume": round(best_run["hypervolume"], 4),
        "Score": round(best_run["score"], 4),
        "ExecTimeSec": round(best_run["exec_time_sec"], 2),
    }
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(row)
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Ejecutar cada instancia N veces con parámetros distintos; semilla aleatoria registrada; guardar métricas y mejores parámetros."
    )
    parser.add_argument(
        "-n", "--num-instances",
        type=int,
        default=999,
        help="Máximo de instancias a procesar (por defecto todas). Orden: mayor a menor tamaño.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=RUNS_PER_INSTANCE,
        help=f"Runs por instancia (default: {RUNS_PER_INSTANCE})",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=RESULTS_BASE,
        help=f"Carpeta de resultados bajo proyecto (default: {RESULTS_BASE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout por ejecución en segundos (default: 600)",
    )
    parser.add_argument(
        "--seed-master",
        type=float,
        default=None,
        help="Semilla maestra para reproducir la elección de parámetros (opcional)",
    )
    args = parser.parse_args()

    n_runs = args.runs
    if args.seed_master is not None:
        random.seed(args.seed_master)
        print(f"Semilla maestra para parámetros: {args.seed_master}")

    instances = tp.get_all_instances()
    if not instances:
        print("ERROR: No se encontraron instancias.")
        sys.exit(1)

    n_instances = min(args.num_instances, len(instances))
    instances = instances[:n_instances]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / args.output_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    # Generar N combinaciones de parámetros (mismas para todas las instancias para comparar)
    param_combinations = generate_param_combinations(n_runs)
    print(f"Combinaciones de parámetros: {n_runs} distintas")
    print(f"Instancias: {n_instances} (orden: mayor a menor tamaño)")
    print(f"Total ejecuciones: {n_instances * n_runs}")
    print(f"Resultados en: {results_dir}")
    print()

    for inst_idx, instance_path in enumerate(instances):
        inst_info = tp.get_instance_info(instance_path)
        instance_name = inst_info["name"]
        print("=" * 60)
        print(f"INSTANCIA [{inst_idx + 1}/{n_instances}]: {instance_name}")
        print(f"  Genes: {inst_info['total_genes']} | Runs: {n_runs}")
        print("=" * 60)

        runs_data = []
        for run_idx in range(n_runs):
            seed = random.uniform(0.001, 0.999)
            param_combo = param_combinations[run_idx]
            pct = 100.0 * (run_idx + 1) / n_runs
            print(f"  Run {run_idx + 1}/{n_runs} ({pct:.0f}%) seed={seed:.4f} "
                  f"pop={param_combo['popsize']} gen={param_combo['ngen']} "
                  f"pc={param_combo['pcross']} pm={param_combo['pmut']} ... ", end="", flush=True)
            result = run_one(instance_path, run_idx + 1, param_combo, seed, timeout=args.timeout)
            if result:
                runs_data.append(result)
                print(f"OK score={result['score']:.4f}")
            else:
                print("FALLO")

        if not runs_data:
            print(f"  Sin resultados válidos para {instance_name}; se omiten CSVs.")
            continue

        runs_data.sort(key=lambda x: -x["score"])
        best_run = runs_data[0]

        path_metrics = save_metrics_csv(results_dir, instance_name, runs_data, timestamp)
        path_best = save_best_csv(results_dir, instance_name, best_run, timestamp)

        print(f"\n  Métricas (todas): {path_metrics.name}")
        print(f"  Mejor run:       {path_best.name}")
        print(f"    Seed={best_run['seed']:.6f} pop={best_run['popsize']} gen={best_run['ngen']} "
              f"pc={best_run['pcross']} pm={best_run['pmut']} -> score={best_run['score']:.4f}")
        print()

    print("Listo. Revisa la carpeta:", results_dir)


if __name__ == "__main__":
    main()
