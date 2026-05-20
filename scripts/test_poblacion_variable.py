#!/usr/bin/env python3
"""
Prueba todas las instancias variando solo el tamaño de población (200 a 4000, paso 100),
manteniendo el resto de parámetros fijos según las métricas indicadas:
  seed aleatoria, ngen=200, pcross=0.9, pmut=0.01

Guarda los resultados por instancia en results/testeo_poblacion_variable.

Uso (desde la raíz del proyecto):
    python3 scripts/test_poblacion_variable.py
    python3 scripts/test_poblacion_variable.py --timeout 1200
"""

import csv
import os
import subprocess
import sys
import random
import time as time_module
from datetime import datetime
from pathlib import Path

# Parámetros fijos (métricas de la instancia de referencia)
#SEED = 0.594808
#Semilla aleatoria 
SEED = random.uniform(0.001, 0.999)
NGEN = 200
PCROSS = 0.9
PMUT = 0.01

# Población: 200 a 4000 (NSGA-II requiere múltiplo de 4)
POP_MIN = 200
POP_MAX = 4000
POP_STEP = 100

# Importar lógica compartida
import tune_parameters as tp

PROJECT_ROOT = Path(tp.PROJECT_ROOT)
EXECUTABLE = str(Path(tp.PROJECT_ROOT) / "build" / "nsga2r")
OUTPUT_DIR = "results/testeo_poblacion_variable"


def run_nsga2_with_timeout(seed, instance_path, popsize, ngen, pcross, pmut, timeout_sec=600):
    """Ejecuta NSGA-II con timeout. Retorna (success, elapsed)."""
    cmd = tp.nsga2_cmd(
        f"{seed:.6f}",
        str(instance_path),
        popsize,
        ngen,
        2,
        pcross,
        pmut,
    )
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


def run_one(instance_path, popsize, timeout=600):
    """Ejecuta NSGA-II una vez con la población dada. Devuelve dict de métricas o None."""
    success, elapsed = run_nsga2_with_timeout(
        seed=SEED,
        instance_path=instance_path,
        popsize=popsize,
        ngen=NGEN,
        pcross=PCROSS,
        pmut=PMUT,
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
        "seed": SEED,
        "popsize": popsize,
        "ngen": NGEN,
        "pcross": PCROSS,
        "pmut": PMUT,
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
        "hv_ref_cost": metrics["hv_ref_cost"],
        "hv_ref_time": metrics["hv_ref_time"],
        "score": score,
        "exec_time_sec": elapsed,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Testear todas las instancias variando población (200–4000, paso 100) con parámetros fijos."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=OUTPUT_DIR,
        help=f"Carpeta de resultados (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout por ejecución en segundos (default: 600)",
    )
    parser.add_argument(
        "-n", "--num-instances",
        type=int,
        default=999,
        help="Máximo de instancias a procesar (default: todas)",
    )
    args = parser.parse_args()

    pop_sizes = list(range(POP_MIN, POP_MAX + 1, POP_STEP))
    instances = tp.get_all_instances()
    if not instances:
        print("ERROR: No se encontraron instancias.")
        sys.exit(1)

    n_instances = min(args.num_instances, len(instances))
    instances = instances[:n_instances]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / args.output_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("TESTS POBLACIÓN VARIABLE (200 → 4000, paso 100)")
    print("=" * 60)
    print(f"Parámetros fijos: seed={SEED}, ngen={NGEN}, pcross={PCROSS}, pmut={PMUT}")
    print(f"Poblaciones: {len(pop_sizes)} valores")
    print(f"Instancias: {n_instances}")
    print(f"Total ejecuciones: {n_instances * len(pop_sizes)}")
    print(f"Resultados en: {results_dir}")
    print()

    for inst_idx, instance_path in enumerate(instances):
        inst_info = tp.get_instance_info(instance_path)
        instance_name = inst_info["name"]
        print("=" * 60)
        print(f"INSTANCIA [{inst_idx + 1}/{n_instances}]: {instance_name}")
        print("=" * 60)

        rows = []
        for i, popsize in enumerate(pop_sizes):
            pct = 100.0 * (i + 1) / len(pop_sizes)
            print(f"  pop={popsize:>4d} ({i + 1}/{len(pop_sizes)}, {pct:>3.0f}%) ... ", end="", flush=True)
            result = run_one(instance_path, popsize, timeout=args.timeout)
            if result:
                rows.append(result)
                print(
                    f"OK  hv={result['hypervolume']:.4f}  "
                    f"#sol={result['unique_solutions']:>3d}  "
                    f"score={result['score']:.4f}  "
                    f"({result['exec_time_sec']:.1f}s)"
                )
            else:
                print("FALLO")

        if not rows:
            print(f"  Sin resultados validos para {instance_name}; se omite CSV.")
            continue

        best = max(rows, key=lambda r: r["score"])
        best_hv = max(rows, key=lambda r: r["hypervolume"])
        print()
        print(f"  --- Resumen {instance_name} ({len(rows)}/{len(pop_sizes)} OK) ---")
        print(f"  Mejor score:  {best['score']:.4f}  (pop={best['popsize']})")
        print(f"  Mejor HV:     {best_hv['hypervolume']:.4f}  (pop={best_hv['popsize']})")
        print(f"  HV ref point: cost={best_hv['hv_ref_cost']:.2f}  time={best_hv['hv_ref_time']:.2f}")
        print(f"  Soluciones:   {best_hv['unique_solutions']} unicas / {best_hv['total_solutions']} totales")
        print(f"  Spread:       cost=[{best_hv['best_cost']:.0f}, {best_hv['worst_cost']:.0f}]  "
              f"time=[{best_hv['best_time']:.0f}, {best_hv['worst_time']:.0f}]")

        out_file = results_dir / f"{instance_name}_poblacion_variable_{timestamp}.csv"
        fieldnames = [
            "Seed", "Popsize", "Ngen", "Pcross", "Pmut",
            "BestCost", "BestTime", "WorstCost", "WorstTime",
            "AvgCost", "AvgTime", "TotalSolutions", "UniqueSolutions",
            "SpreadCost", "SpreadTime", "Hypervolume",
            "HvRefCost", "HvRefTime",
            "Score", "ExecTimeSec",
        ]
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                row = {
                    "Seed": f"{r['seed']:.6f}",
                    "Popsize": r["popsize"],
                    "Ngen": r["ngen"],
                    "Pcross": r["pcross"],
                    "Pmut": r["pmut"],
                    "BestCost": round(r["best_cost"], 2),
                    "BestTime": round(r["best_time"], 2),
                    "WorstCost": round(r["worst_cost"], 2),
                    "WorstTime": round(r["worst_time"], 2),
                    "AvgCost": round(r["avg_cost"], 2),
                    "AvgTime": round(r["avg_time"], 2),
                    "TotalSolutions": r["total_solutions"],
                    "UniqueSolutions": r["unique_solutions"],
                    "SpreadCost": round(r["spread_cost"], 2),
                    "SpreadTime": round(r["spread_time"], 2),
                    "Hypervolume": round(r["hypervolume"], 4),
                    "HvRefCost": round(r["hv_ref_cost"], 2),
                    "HvRefTime": round(r["hv_ref_time"], 2),
                    "Score": round(r["score"], 4),
                    "ExecTimeSec": round(r["exec_time_sec"], 2),
                }
                w.writerow(row)

        print(f"  Guardado: {out_file.name}\n")

    print("Listo. Revisa la carpeta:", results_dir)


if __name__ == "__main__":
    main()
