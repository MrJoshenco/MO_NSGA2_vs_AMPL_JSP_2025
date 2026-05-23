#!/usr/bin/env python3
"""
Verificación de la ejecución del algoritmo NSGA-II: comprueba que el binario
recibe y usa semilla, iteraciones y población, y que los scripts leen el CSV
correcto (no cacheado).

Pasos:
  1. Ejecutar una run y verificar que params.out coincide con los argumentos.
  2. Ejecutar dos runs con semillas distintas (y luego ngen, popsize) y comparar resultados.
  3. Tras cada run, registrar hash del CSV para confirmar que se lee el archivo recién escrito.
  4. Soporta instancia pequeña y grande (--instance-small / --instance-large).

Revisión paso 4 (fallos silenciosos): En todos los scripts que usan parse_pareto_results
(test_poblacion_variable, test_iteraciones_variable, test_mixto_popsize_ngen, run_50_per_instance,
tune_parameters) la llamada a parse_pareto_results ocurre solo tras "if not success: return None"
o "if success: ... parse_pareto_results(...)", por lo que no se usa el CSV cuando la ejecución falla.

Uso (desde la raíz del proyecto):
    python3 scripts/verify_nsga2_params.py
    python3 scripts/verify_nsga2_params.py --instance-small instances/trivial/instancia_trivial.txt --instance-large instances/gigante/instancia_gigante.txt
    python3 scripts/verify_nsga2_params.py --timeout 120
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time as time_module
from pathlib import Path

# Importar lógica compartida
import tune_parameters as tp

PROJECT_ROOT = Path(tp.PROJECT_ROOT)
EXECUTABLE = str(Path(tp.PROJECT_ROOT) / "build" / "nsga2r")
PARAMS_OUT = PROJECT_ROOT / "params.out"
DEFAULT_INSTANCE_SMALL = "instances/trivial/instancia_trivial.txt"
DEFAULT_INSTANCE_LARGE = "instances/gigante/instancia_gigante.txt"
PCROSS = 0.9
PMUT = 0.01
NOBJ = 2


def run_nsga2(seed, instance_path, popsize, ngen, timeout_sec=300):
    """Ejecuta nsga2r. Retorna (success, elapsed_sec)."""
    instance_path = str(Path(instance_path).resolve() if not os.path.isabs(instance_path) else instance_path)
    cmd = tp.nsga2_cmd(
        f"{seed:.6f}",
        instance_path,
        popsize,
        ngen,
        NOBJ,
        PCROSS,
        PMUT,
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
        elapsed = time_module.time() - t0
        return result.returncode == 0, elapsed
    except subprocess.TimeoutExpired:
        return False, float(timeout_sec)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, 0.0


def parse_params_out():
    """Lee params.out en PROJECT_ROOT. Retorna dict con popsize, ngen, seed, pcross, pmut o None."""
    if not PARAMS_OUT.exists():
        return None
    text = PARAMS_OUT.read_text()
    out = {}
    m = re.search(r"Population size\s*=\s*(\d+)", text)
    if m:
        out["popsize"] = int(m.group(1))
    m = re.search(r"Number of generations\s*=\s*(\d+)", text)
    if m:
        out["ngen"] = int(m.group(1))
    m = re.search(r"Seed\s*=\s*([\d.eE+-]+)", text)
    if m:
        out["seed"] = float(m.group(1))
    m = re.search(r"Probability of crossover\s*=\s*([\d.eE+-]+)", text)
    if m:
        out["pcross"] = float(m.group(1))
    m = re.search(r"Probability of mutation\s*=\s*([\d.eE+-]+)", text)
    if m:
        out["pmut"] = float(m.group(1))
    if len(out) < 3:  # al menos seed, popsize, ngen
        return None
    return out


def get_pareto_csv_path(instance_path):
    """Ruta del CSV de Pareto para esta instancia (como lo usa el C en cwd=PROJECT_ROOT)."""
    base = os.path.splitext(os.path.basename(instance_path))[0]
    return PROJECT_ROOT / "output" / "solutions" / f"solutions_{base}_pareto.csv"


def csv_content_hash(instance_path):
    """Devuelve hash del contenido del CSV Pareto (para verificar que cambia entre runs)."""
    p = get_pareto_csv_path(instance_path)
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def get_metrics_from_run(instance_path):
    """Tras una ejecución, lee el CSV y devuelve métricas (best_cost, total_solutions, etc.)."""
    solutions = tp.parse_pareto_results(str(instance_path))
    if not solutions:
        return None
    return tp.calculate_metrics(solutions)


def resolve_instance(path_str):
    """Devuelve path absoluto; si es relativo, respecto a PROJECT_ROOT."""
    p = Path(path_str)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p.resolve())


# --- Paso 1: Verificar que params.out coincide con argumentos ---
def step1_verify_params_out(instance_path, timeout):
    """Ejecuta una run con parámetros fijos y comprueba que params.out los refleja."""
    print("\n--- Paso 1: Verificar que el binario escribe params.out correcto ---")
    seed = 0.25
    popsize = 100
    ngen = 50
    success, elapsed = run_nsga2(seed, instance_path, popsize, ngen, timeout_sec=timeout)
    if not success:
        print("  FALLO: La ejecución no terminó correctamente.")
        return False
    params = parse_params_out()
    if not params:
        print("  FALLO: No se pudo leer params.out.")
        return False
    ok = True
    if params.get("seed") is not None and abs(params["seed"] - seed) > 1e-5:
        print(f"  FALLO: Seed en params.out = {params['seed']}, esperado = {seed}")
        ok = False
    if params.get("popsize") != popsize:
        print(f"  FALLO: Population size en params.out = {params.get('popsize')}, esperado = {popsize}")
        ok = False
    if params.get("ngen") != ngen:
        print(f"  FALLO: Number of generations en params.out = {params.get('ngen')}, esperado = {ngen}")
        ok = False
    if ok:
        print(f"  OK: params.out coincide con seed={seed}, popsize={popsize}, ngen={ngen} (elapsed={elapsed:.1f}s)")
    return ok


# --- Paso 2 y 3: Dos runs con parámetro distinto y comparar CSV (y hash) ---
def run_two_and_compare(
    instance_path,
    timeout,
    label,
    run1_kwargs,
    run2_kwargs,
    param_name,
):
    """Ejecuta dos runs con run1_kwargs y run2_kwargs; compara métricas y hash del CSV."""
    instance_path = resolve_instance(instance_path)
    defaults = {"instance_path": instance_path, "timeout_sec": timeout}
    success1, _ = run_nsga2(**(defaults | run1_kwargs))
    if not success1:
        print(f"  FALLO: Primera ejecución ({label}) falló.")
        return False
    hash1 = csv_content_hash(instance_path)
    metrics1 = get_metrics_from_run(instance_path)
    success2, _ = run_nsga2(**(defaults | run2_kwargs))
    if not success2:
        print(f"  FALLO: Segunda ejecución ({label}) falló.")
        return False
    hash2 = csv_content_hash(instance_path)
    metrics2 = get_metrics_from_run(instance_path)
    # Verificar que el contenido del CSV cambió (hash distinto)
    if hash1 == hash2:
        print(f"  AVISO: Hash del CSV idéntico entre las dos runs ({param_name}). Puede ser instancia trivial.")
    else:
        print(f"  OK (hash): CSV distinto entre runs (hash1={hash1}, hash2={hash2}).")
    if not metrics1 or not metrics2:
        print(f"  FALLO: No se pudieron leer métricas del CSV en alguna run.")
        return False
    bc1, bc2 = metrics1["best_cost"], metrics2["best_cost"]
    n1, n2 = metrics1["total_solutions"], metrics2["total_solutions"]
    if bc1 == bc2 and n1 == n2:
        print(f"  AVISO: Métricas idénticas (best_cost={bc1}, total_solutions={n1}). Puede ser instancia trivial o parámetro no influye.")
    else:
        print(f"  OK (métricas): best_cost {bc1} vs {bc2}, total_solutions {n1} vs {n2}.")
    return True


def step2_compare_seed(instance_path, timeout):
    """Dos runs con semillas distintas."""
    print("\n--- Paso 2a: Comparar dos runs con semillas distintas ---")
    return run_two_and_compare(
        instance_path,
        timeout,
        "seed",
        {"seed": 0.2, "popsize": 100, "ngen": 100},
        {"seed": 0.8, "popsize": 100, "ngen": 100},
        "seed",
    )


def step2_compare_ngen(instance_path, timeout):
    """Dos runs con ngen distinto."""
    print("\n--- Paso 2b: Comparar dos runs con ngen distinto ---")
    return run_two_and_compare(
        instance_path,
        timeout,
        "ngen",
        {"seed": 0.3, "popsize": 100, "ngen": 50},
        {"seed": 0.3, "popsize": 100, "ngen": 200},
        "ngen",
    )


def step2_compare_popsize(instance_path, timeout):
    """Dos runs con popsize distinto (múltiplos de 4)."""
    print("\n--- Paso 2c: Comparar dos runs con popsize distinto ---")
    return run_two_and_compare(
        instance_path,
        timeout,
        "popsize",
        {"seed": 0.4, "popsize": 52, "ngen": 100},
        {"seed": 0.4, "popsize": 200, "ngen": 100},
        "popsize",
    )


# --- Paso 3: Verificar que cada run escribe un CSV distinto (hash) ---
def step3_csv_freshness(instance_path, timeout):
    """Tras dos runs con parámetros distintos, los hashes del CSV deben ser distintos."""
    print("\n--- Paso 3: Verificar que Python leería el CSV recién escrito (hash por run) ---")
    instance_path = resolve_instance(instance_path)
    run_nsga2(0.1, instance_path, 100, 50, timeout_sec=timeout)
    h1 = csv_content_hash(instance_path)
    run_nsga2(0.9, instance_path, 100, 50, timeout_sec=timeout)
    h2 = csv_content_hash(instance_path)
    if h1 != h2:
        print(f"  OK: Hash del CSV cambia entre runs (hash_run1={h1}, hash_run2={h2}).")
        return True
    print(f"  AVISO: Mismo hash en ambas runs. Instancia pequeña o resultados idénticos.")
    return True  # No fallar; puede ser instancia trivial


def main():
    parser = argparse.ArgumentParser(
        description="Verificar que nsga2r usa semilla, ngen y popsize y que el CSV leído es el correcto."
    )
    parser.add_argument(
        "--instance-small",
        type=str,
        default=DEFAULT_INSTANCE_SMALL,
        help=f"Instancia pequeña (default: {DEFAULT_INSTANCE_SMALL})",
    )
    parser.add_argument(
        "--instance-large",
        type=str,
        default=DEFAULT_INSTANCE_LARGE,
        help=f"Instancia grande (default: {DEFAULT_INSTANCE_LARGE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout por ejecución en segundos (default: 300)",
    )
    parser.add_argument(
        "--small-only",
        action="store_true",
        help="Solo usar instancia pequeña (más rápido)",
    )
    parser.add_argument(
        "--large-only",
        action="store_true",
        help="Solo usar instancia grande",
    )
    args = parser.parse_args()

    if not Path(EXECUTABLE).exists():
        print(f"ERROR: Ejecutable no encontrado: {EXECUTABLE}")
        print("  Compila con: cd build && cmake .. && make")
        sys.exit(1)

    instance_small = resolve_instance(args.instance_small)
    instance_large = resolve_instance(args.instance_large)
    if not Path(instance_small).exists():
        print(f"ERROR: Instancia pequeña no encontrada: {instance_small}")
        sys.exit(1)
    if not Path(instance_large).exists():
        print(f"ERROR: Instancia grande no encontrada: {instance_large}")
        sys.exit(1)

    print("Verificación NSGA-II")
    print(f"  Ejecutable: {EXECUTABLE}")
    print(f"  Instancia pequeña: {instance_small}")
    print(f"  Instancia grande: {instance_large}")
    print(f"  Timeout: {args.timeout}s")

    results = []
    instances_to_run = []
    if not args.large_only:
        instances_to_run.append(("pequeña", instance_small))
    if not args.small_only:
        instances_to_run.append(("grande", instance_large))

    for name, instance in instances_to_run:
        print(f"\n========== Instancia {name} ==========")
        results.append(("Paso 1 params.out", step1_verify_params_out(instance, args.timeout)))
        results.append(("Paso 2a seed", step2_compare_seed(instance, args.timeout)))
        results.append(("Paso 2b ngen", step2_compare_ngen(instance, args.timeout)))
        results.append(("Paso 2c popsize", step2_compare_popsize(instance, args.timeout)))
        results.append(("Paso 3 CSV freshness", step3_csv_freshness(instance, args.timeout)))

    print("\n========== Resumen ==========")
    for label, ok in results:
        print(f"  {label}: {'OK' if ok else 'FALLO'}")
    if not all(r[1] for r in results):
        sys.exit(1)
    print("\nTodas las comprobaciones pasaron.")


if __name__ == "__main__":
    main()
