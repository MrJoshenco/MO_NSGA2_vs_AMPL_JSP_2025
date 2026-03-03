#!/usr/bin/env python3
"""
Prueba todas las instancias con combinaciones de valores altos de Popsize x Ngen
(ej. 6400x6400, 6400x7200, 7200x6400, ...). Resto de parámetros fijos: seed, pcross, pmut.

Guarda los resultados por instancia en results/testeo_mixto_popsize_ngen.

Uso (desde la raíz del proyecto):
    python3 scripts/test_mixto_popsize_ngen.py
    python3 scripts/test_mixto_popsize_ngen.py --timeout 1200
"""

import csv
import subprocess
import sys
import time as time_module
from datetime import datetime
from pathlib import Path

# Parámetros fijos
SEED = 0.594808
PCROSS = 0.9
PMUT = 0.01

# Valores altos para Popsize y Ngen (múltiplos de 4). Se prueban todas las combinaciones.
# Ejemplo: 6400, 6800, 7200, 7600, 8000 -> 5x5 = 25 combinaciones por instancia
VALUES_MIN = 6400
VALUES_MAX = 8000
VALUES_STEP = 400

# Importar lógica compartida
import tune_parameters as tp

PROJECT_ROOT = Path(tp.PROJECT_ROOT)
EXECUTABLE = str(Path(tp.PROJECT_ROOT) / "build" / "nsga2r")
OUTPUT_DIR = "results/testeo_mixto_popsize_ngen"


def run_nsga2_with_timeout(seed, instance_path, popsize, ngen, pcross, pmut, timeout_sec=600):
    """Ejecuta NSGA-II con timeout. Retorna (success, elapsed, error_msg)."""
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
        elapsed = time_module.time() - t0
        if result.returncode != 0:
            err = (result.stderr or "").strip() or (result.stdout or "").strip()
            return False, elapsed, f"returncode={result.returncode} stderr: {err[:500]}"
        return True, elapsed, None
    except subprocess.TimeoutExpired as e:
        return False, float(timeout_sec), "TIMEOUT"
    except FileNotFoundError:
        return False, 0.0, f"Ejecutable no encontrado: {EXECUTABLE}"
    except Exception as e:
        return False, 0.0, str(e)[:500]


def run_one(instance_path, popsize, ngen, timeout=600, verbose_fail=True):
    """Ejecuta NSGA-II una vez con (popsize, ngen). Devuelve dict de métricas o None."""
    success, elapsed, error_msg = run_nsga2_with_timeout(
        seed=SEED,
        instance_path=instance_path,
        popsize=popsize,
        ngen=ngen,
        pcross=PCROSS,
        pmut=PMUT,
        timeout_sec=timeout,
    )
    if not success:
        if verbose_fail and error_msg:
            print(f" [{error_msg}]", flush=True)
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
        "ngen": ngen,
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
        "score": score,
        "exec_time_sec": elapsed,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Combinaciones de Popsize x Ngen (valores altos, ej. 6400–8000) con parámetros fijos."
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
        default=3600,
        help="Timeout por ejecución en segundos (default: 3600; para 6400x6400 puede hacer falta 7200+)",
    )
    parser.add_argument(
        "-n", "--num-instances",
        type=int,
        default=999,
        help="Máximo de instancias a procesar (default: todas)",
    )
    args = parser.parse_args()

    values = list(range(VALUES_MIN, VALUES_MAX + 1, VALUES_STEP))
    combinations = [(p, g) for p in values for g in values]

    if not Path(EXECUTABLE).exists():
        print(f"ERROR: Ejecutable no encontrado: {EXECUTABLE}")
        print("  Compila con: cd build && cmake .. && make (o make nsga2r)")
        sys.exit(1)

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
    print("TESTS MIXTO: Popsize x Ngen (valores altos)")
    print("=" * 60)
    print(f"Parámetros fijos: seed={SEED}, pcross={PCROSS}, pmut={PMUT}")
    print(f"Valores: {values}")
    print(f"Combinaciones: {len(combinations)} (ej. 6400x6400, 6400x7200, ...)")
    print(f"Instancias: {n_instances}")
    print(f"Total ejecuciones: {n_instances * len(combinations)}")
    print(f"Resultados en: {results_dir}")
    print()

    for inst_idx, instance_path in enumerate(instances):
        inst_info = tp.get_instance_info(instance_path)
        instance_name = inst_info["name"]
        print("=" * 60)
        print(f"INSTANCIA [{inst_idx + 1}/{n_instances}]: {instance_name}")
        print("=" * 60)

        rows = []
        for i, (popsize, ngen) in enumerate(combinations):
            pct = 100.0 * (i + 1) / len(combinations)
            print(f"  pop={popsize} ngen={ngen} ({i + 1}/{len(combinations)}, {pct:.0f}%) ... ", end="", flush=True)
            result = run_one(instance_path, popsize, ngen, timeout=args.timeout)
            if result:
                rows.append(result)
                print(f"OK score={result['score']:.4f} cost={result['best_cost']:.0f}")
            else:
                print("FALLO")

        if not rows:
            print(f"  Sin resultados válidos para {instance_name}; se omite CSV.")
            continue

        out_file = results_dir / f"{instance_name}_mixto_popsize_ngen_{timestamp}.csv"
        fieldnames = [
            "Seed", "Popsize", "Ngen", "Pcross", "Pmut",
            "BestCost", "BestTime", "WorstCost", "WorstTime",
            "AvgCost", "AvgTime", "TotalSolutions", "UniqueSolutions",
            "SpreadCost", "SpreadTime", "Hypervolume", "Score", "ExecTimeSec",
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
                    "Score": round(r["score"], 4),
                    "ExecTimeSec": round(r["exec_time_sec"], 2),
                }
                w.writerow(row)

        print(f"\n  Guardado: {out_file.name}\n")

    print("Listo. Revisa la carpeta:", results_dir)


if __name__ == "__main__":
    main()
