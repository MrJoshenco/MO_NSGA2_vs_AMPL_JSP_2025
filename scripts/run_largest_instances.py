#!/usr/bin/env python3
"""
Ejecuta las instancias más grandes con semilla aleatoria en cada run.
Usa los parámetros ganadores del tuning: popsize=200, ngen=500, pcross=0.8, pmut=0.01.

Uso (desde la raíz del proyecto):
    python3 scripts/run_largest_instances.py              # 3 instancias más grandes, 1 run cada una
    python3 scripts/run_largest_instances.py -n 5       # 5 instancias más grandes
    python3 scripts/run_largest_instances.py -r 3       # 3 runs por instancia (3 semillas aleatorias cada una)
    python3 scripts/run_largest_instances.py -n 2 -r 5  # 2 instancias, 5 runs por instancia
"""

import os
import random
import subprocess
import sys
from pathlib import Path

# Raíz del proyecto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
EXECUTABLE = PROJECT_ROOT / "build" / "nsga2r"
INSTANCES_DIR = PROJECT_ROOT / "instances"

# Parámetros ganadores del tuning (sin semilla)
POPSIZE = 200
NGEN = 500
NOBJ = 2
PCROSS = 0.8
PMUT = 0.01


def get_instance_info(instance_path):
    """Extrae jobs, machines, ops y total_genes del archivo .txt."""
    name = instance_path.stem
    jobs = machines = ops = 0
    try:
        with open(instance_path, "r") as f:
            parts = f.readline().strip().split()
            if len(parts) >= 3:
                jobs, machines, ops = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        pass
    total_genes = jobs * ops if (jobs and ops) else 0
    return {"name": name, "path": instance_path, "total_genes": total_genes}


def get_largest_instances(n=3):
    """Devuelve las n instancias más grandes (ordenadas por total_genes descendente)."""
    if not INSTANCES_DIR.exists():
        return []
    paths = list(INSTANCES_DIR.rglob("instancia*.txt"))
    with_info = [get_instance_info(p) for p in paths]
    with_info.sort(key=lambda x: -x["total_genes"])
    return [x["path"] for x in with_info[:n]]


def run_nsga2(instance_path, seed, timeout=600):
    """Ejecuta NSGA-II; instance_path es Path o str, seed en (0, 1)."""
    cmd = [
        str(EXECUTABLE),
        f"{seed:.6f}",
        str(instance_path),
        str(POPSIZE),
        str(NGEN),
        str(NOBJ),
        str(PCROSS),
        str(PMUT),
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ejecutar instancias grandes con semilla aleatoria.")
    parser.add_argument(
        "-n", "--num-instances",
        type=int,
        default=3,
        help="Número de instancias más grandes a ejecutar (default: 3)",
    )
    parser.add_argument(
        "-r", "--runs-per-instance",
        type=int,
        default=1,
        help="Runs por instancia, cada uno con semilla aleatoria distinta (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout por ejecución en segundos (default: 600)",
    )
    args = parser.parse_args()

    if not EXECUTABLE.exists():
        print(f"ERROR: No se encontró el ejecutable {EXECUTABLE}")
        print("Compila con: make")
        sys.exit(1)

    instances = get_largest_instances(args.num_instances)
    if not instances:
        print("ERROR: No se encontraron instancias en", INSTANCES_DIR)
        sys.exit(1)

    print("Instancias (mayor a menor tamaño):")
    for p in instances:
        info = get_instance_info(p)
        print(f"  - {info['name']} ({info['total_genes']} genes)")
    print(f"\nParámetros: pop={POPSIZE}, gen={NGEN}, pcross={PCROSS}, pmut={PMUT}")
    print(f"Total runs: {len(instances) * args.runs_per_instance} (semilla aleatoria en (0,1) por run)\n")

    ok = 0
    for inst_path in instances:
        name = inst_path.stem
        for r in range(args.runs_per_instance):
            seed = random.uniform(0.001, 0.999)
            print(f"[{name}] run {r+1}/{args.runs_per_instance} seed={seed:.4f} ... ", end="", flush=True)
            if run_nsga2(inst_path, seed, timeout=args.timeout):
                print("OK")
                ok += 1
            else:
                print("FALLO")
    print(f"\nCompletados: {ok}/{len(instances) * args.runs_per_instance}")


if __name__ == "__main__":
    main()
