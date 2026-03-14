#!/usr/bin/env python3
"""
Prueba todas las instancias con combinaciones de Popsize x Ngen
(200..4000 x 200..4000, paso configurable). Resto de parámetros fijos: seed, pcross, pmut.

Guarda los resultados por instancia en results/testeo_mixto_popsize_ngen.
Cada resultado se escribe al CSV en cuanto termina (guardado incremental).
Puedes interrumpir con Ctrl+C y reanudar después con --resume.

Uso (desde la raíz del proyecto):
    python3 scripts/test_mixto_popsize_ngen.py
    python3 scripts/test_mixto_popsize_ngen.py --timeout 1200
    python3 scripts/test_mixto_popsize_ngen.py --pop-step 400 --ngen-step 400
    python3 scripts/test_mixto_popsize_ngen.py --resume results/testeo_mixto_popsize_ngen/run_20250305_123456
"""

import csv
import json
import random
import subprocess
import sys
import time as time_module
from datetime import datetime
from pathlib import Path

# Parámetros fijos
SEED = random.uniform(0.001, 0.999)
PCROSS = 0.9
PMUT = 0.01

# Rangos para Popsize y Ngen (múltiplos de 4)
POP_MIN = 200
POP_MAX = 4000
POP_STEP = 200

NGEN_MIN = 200
NGEN_MAX = 4000
NGEN_STEP = 200

# Importar lógica compartida
import tune_parameters as tp

PROJECT_ROOT = Path(tp.PROJECT_ROOT)
EXECUTABLE = str(Path(tp.PROJECT_ROOT) / "build" / "nsga2r")
OUTPUT_DIR = "results/testeo_mixto_popsize_ngen"
CHECKPOINT_FILENAME = "checkpoint.json"

CSV_FIELDNAMES = [
    "Seed", "Popsize", "Ngen", "Pcross", "Pmut",
    "BestCost", "BestTime", "WorstCost", "WorstTime",
    "AvgCost", "AvgTime", "TotalSolutions", "UniqueSolutions",
    "SpreadCost", "SpreadTime", "Hypervolume",
    "HvRefCost", "HvRefTime",
    "Score", "ExecTimeSec",
]


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
        "hv_ref_cost": metrics["hv_ref_cost"],
        "hv_ref_time": metrics["hv_ref_time"],
        "score": score,
        "exec_time_sec": elapsed,
    }


def result_to_csv_row(r):
    """Convierte un dict de resultado en la fila para el CSV."""
    return {
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


def save_checkpoint(run_dir, seed, instance_index, instance_name, completed_combinations):
    """Guarda checkpoint para poder reanudar luego."""
    path = Path(run_dir) / CHECKPOINT_FILENAME
    data = {
        "seed": seed,
        "instance_index": instance_index,
        "instance_name": instance_name,
        "completed_combinations": completed_combinations,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_checkpoint(run_dir):
    """Carga checkpoint; devuelve None si no existe o está corrupto."""
    path = Path(run_dir) / CHECKPOINT_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def append_result_to_csv(csv_path, result, write_header=False):
    """Añade una fila al CSV (crea el archivo con cabecera si write_header)."""
    path = Path(csv_path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if write_header:
            w.writeheader()
        w.writerow(result_to_csv_row(result))


def main():
    import argparse
    global SEED
    parser = argparse.ArgumentParser(
        description="Combinaciones de Popsize x Ngen (200-4000) con parámetros fijos."
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
    parser.add_argument(
        "--pop-step", type=int, default=POP_STEP,
        help=f"Paso para popsize (default: {POP_STEP})",
    )
    parser.add_argument(
        "--ngen-step", type=int, default=NGEN_STEP,
        help=f"Paso para ngen (default: {NGEN_STEP})",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="RUN_DIR",
        help="Reanudar desde una ejecución anterior (ruta a la carpeta run_YYYYMMDD_HHMMSS)",
    )
    args = parser.parse_args()

    pop_values = list(range(POP_MIN, POP_MAX + 1, args.pop_step))
    ngen_values = list(range(NGEN_MIN, NGEN_MAX + 1, args.ngen_step))
    combinations = [(p, g) for p in pop_values for g in ngen_values]

    if not Path(EXECUTABLE).exists():
        print(f"ERROR: Ejecutable no encontrado: {EXECUTABLE}")
        sys.exit(1)

    instances = tp.get_all_instances()
    if not instances:
        print("ERROR: No se encontraron instancias.")
        sys.exit(1)

    n_instances_total = min(args.num_instances, len(instances))
    base_instances = instances[:n_instances_total]

    # Resolución de run_dir y checkpoint (nueva ejecución vs reanudar)
    resume_dir = Path(args.resume).resolve() if args.resume else None
    if resume_dir is not None:
        cp = load_checkpoint(resume_dir)
        if not cp:
            print(f"ERROR: No se pudo cargar checkpoint en {resume_dir}")
            sys.exit(1)
        run_dir = resume_dir
        SEED = cp["seed"]
        start_inst_idx = cp["instance_index"]
        completed_set = set(tuple(x) for x in cp["completed_combinations"])
        instances = base_instances[start_inst_idx:]
        n_instances = len(instances)
        print("=" * 70)
        print("REANUDANDO EJECUCIÓN")
        print("=" * 70)
        print(f"Run dir: {run_dir}")
        print(f"Seed: {SEED:.6f}")
        print(f"Instancia actual: {cp['instance_name']} (índice {start_inst_idx + 1}/{n_instances_total})")
        print(f"Combinaciones ya hechas en esta instancia: {len(completed_set)}/{len(combinations)}")
        print()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_base = PROJECT_ROOT / args.output_dir
        results_base.mkdir(parents=True, exist_ok=True)
        run_dir = results_base / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        start_inst_idx = 0
        completed_set = set()
        instances = base_instances
        n_instances = len(instances)
        save_checkpoint(run_dir, SEED, 0, "", [])

    results_dir = run_dir

    print("=" * 70)
    print("TESTS MIXTO: Popsize x Ngen")
    print("=" * 70)
    print(f"Parametros fijos: seed={SEED:.6f}, pcross={PCROSS}, pmut={PMUT}")
    print(f"Popsize:  {pop_values[0]}..{pop_values[-1]} (paso {args.pop_step}, {len(pop_values)} valores)")
    print(f"Ngen:     {ngen_values[0]}..{ngen_values[-1]} (paso {args.ngen_step}, {len(ngen_values)} valores)")
    print(f"Combinaciones: {len(combinations)}")
    print(f"Instancias por procesar: {n_instances}")
    print(f"Resultados en: {results_dir}")
    if resume_dir:
        print("Modo: REANUDAR (combinaciones ya hechas se omiten)")
    print()

    for rel_idx, instance_path in enumerate(instances):
        inst_idx = start_inst_idx + rel_idx
        inst_info = tp.get_instance_info(instance_path)
        instance_name = inst_info["name"]
        csv_path = results_dir / f"{instance_name}_mixto_popsize_ngen.csv"
        write_header = not csv_path.exists()

        print("=" * 70)
        print(f"INSTANCIA [{inst_idx + 1}/{n_instances_total}]: {instance_name}")
        print("=" * 70)

        rows_this_run = []
        for i, (popsize, ngen) in enumerate(combinations):
            if (popsize, ngen) in completed_set:
                print(f"  pop={popsize:>4d} ngen={ngen:>4d} ({i + 1}/{len(combinations)}) ... omitido (ya hecho)", flush=True)
                continue
            pct = 100.0 * (i + 1) / len(combinations)
            print(f"  pop={popsize:>4d} ngen={ngen:>4d} ({i + 1}/{len(combinations)}, {pct:>3.0f}%) ... ", end="", flush=True)
            result = run_one(instance_path, popsize, ngen, timeout=args.timeout)
            if result:
                append_result_to_csv(csv_path, result, write_header=write_header)
                write_header = False
                completed_set.add((popsize, ngen))
                save_checkpoint(
                    run_dir, SEED, inst_idx, instance_name,
                    list(completed_set),
                )
                rows_this_run.append(result)
                print(
                    f"OK  hv={result['hypervolume']:.4f}  "
                    f"#sol={result['unique_solutions']:>3d}  "
                    f"score={result['score']:.4f}  "
                    f"({result['exec_time_sec']:.1f}s)"
                )
            else:
                print("FALLO")

        completed_set.clear()
        save_checkpoint(run_dir, SEED, inst_idx + 1, "", [])

        # Resumen por instancia (usando solo filas de esta sesión si quieres; aquí mostramos lo que hay en CSV)
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except OSError:
            rows = []
        if rows:
            def score_key(r):
                return float(r["Score"])
            def hv_key(r):
                return float(r["Hypervolume"])
            best = max(rows, key=score_key)
            best_hv = max(rows, key=hv_key)
            print()
            print(f"  --- Resumen {instance_name} ({len(rows)}/{len(combinations)} OK) ---")
            print(f"  Mejor score:  {best['Score']}  (pop={best['Popsize']}, ngen={best['Ngen']})")
            print(f"  Mejor HV:     {best_hv['Hypervolume']}  (pop={best_hv['Popsize']}, ngen={best_hv['Ngen']})")
            print(f"  Guardado: {csv_path.name}\n")
        else:
            print(f"  Sin resultados validos para {instance_name}; se omite resumen.\n")

    print("Listo. Revisa la carpeta:", results_dir)


if __name__ == "__main__":
    main()
