#!/usr/bin/env python3
"""
Ejecuta NSGA-II varias veces para UNA instancia con parámetros fijos y
acumula las soluciones únicas (sin hypervolume, sin métricas agregadas).

Deduplicación:
  Una solución se considera única si coincide el par (Cost, Time), usando
  costo_total y tiempo_total del CSV Pareto: output/solutions/*_pareto.csv.

Persistencia / append:
  - Si el script se ejecuta otra vez, carga el CSV existente y solo
    agrega filas nuevas (soluciones únicas no vistas antes).

Columnas en el CSV final:
  Seed, Popsize, Ngen, Pcross, Pmut, Cost, Time, CrowdingDistance, ExecTimeSec
  (ExecTimeSec = tiempo NSGA-II reportado en solutions_*_pareto.csv; si falta, wall-clock del subprocess)
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time as time_module
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tune_parameters as tp


# ============================
# PARAMETROS FIJOS (editar)
# ============================
POP_SIZE = 1000
NGEN = 4000
PCROSS = 0.9
PMUT = 0.01
NOBJ = 2
ENABLE_DIVERSITY = 1
ENABLE_PARTIAL_RESTART = 1
ENABLE_PRESERVATION = 1

# Semilla(s) para esta ejecucion (edita este valor y/o la lista).
SEED = 0.1
SEEDS = [SEED, 0.92, 0.33, 0.55, 0.67, 0.21, 0.18, 0.64]


def fmt_float_for_filename(x: float) -> str:
    """Convierte un float a string seguro para nombre de archivo."""
    s = f"{x}".strip()
    # Evita caracteres problemáticos en nombres de archivos.
    return s.replace(".", "_").replace("-", "m")


def nsga2_executable(project_root: Path) -> Path:
    return project_root / "build" / "nsga2r"


def run_nsga2_with_timeout(
    *,
    executable: Path,
    project_root: Path,
    seed: float,
    instance_path: Path,
    popsize: int,
    ngen: int,
    pcross: float,
    pmut: float,
    nobj: int = 2,
    enable_diversity: int = ENABLE_DIVERSITY,
    enable_partial_restart: int = ENABLE_PARTIAL_RESTART,
    enable_preservation: int = ENABLE_PRESERVATION,
    timeout_sec: int = 600,
) -> Tuple[bool, float, str | None]:
    """Ejecuta nsga2r y retorna (success, elapsed, error_msg)."""
    cmd = tp.nsga2_cmd(
        f"{seed:.6f}",
        str(instance_path),
        popsize,
        ngen,
        nobj,
        pcross,
        pmut,
        enable_diversity=enable_diversity,
        enable_partial_restart=enable_partial_restart,
        enable_preservation=enable_preservation,
    )
    cmd[0] = str(executable)

    try:
        t0 = time_module.time()
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        elapsed = time_module.time() - t0
        if result.returncode != 0:
            err = (result.stderr or "").strip() or (result.stdout or "").strip()
            return False, elapsed, f"returncode={result.returncode} stderr: {err[:500]}"
        return True, elapsed, None
    except subprocess.TimeoutExpired:
        return False, float(timeout_sec), "TIMEOUT"
    except FileNotFoundError:
        return False, 0.0, f"Ejecutable no encontrado: {executable}"
    except Exception as e:
        return False, 0.0, str(e)[:500]


def pareto_csv_path(project_root: Path, instance_path: Path) -> Path:
    base = instance_path.stem
    return project_root / "output" / "solutions" / f"solutions_{base}_pareto.csv"


def parse_pareto_file(
    instance_path: Path, project_root: Path
) -> Tuple[List[Dict[str, str]], Optional[float]]:
    """
    Lee output/solutions/solutions_{base}_pareto.csv.

    Retorna (soluciones, exec_time_sec).
    exec_time_sec se lee de la línea '# exec_time_sec=...' si existe.
    """
    path = pareto_csv_path(project_root, instance_path)
    if not path.exists():
        return [], None

    solutions: List[Dict[str, str]] = []
    exec_time_sec: Optional[float] = None

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            cell0 = row[0].strip()
            if cell0.startswith("# exec_time_sec="):
                try:
                    exec_time_sec = float(cell0.split("=", 1)[1].strip())
                except ValueError:
                    pass
                continue
            if cell0.startswith("#"):
                continue
            if cell0 == "solucion":
                continue
            if len(row) < 4:
                continue
            try:
                cost_val = float(row[1].strip())
                time_val = float(row[2].strip())
            except ValueError:
                continue

            solutions.append(
                {
                    "Cost": f"{cost_val:.2f}",
                    "Time": f"{time_val:.2f}",
                    "CrowdingDistance": row[3].strip(),
                }
            )

    return solutions, exec_time_sec


def parse_pareto_solutions(instance_path: Path, project_root: Path) -> List[Dict[str, str]]:
    """Compat: solo la lista de soluciones."""
    solutions, _ = parse_pareto_file(instance_path, project_root)
    return solutions


FIELDNAMES = [
    "Seed",
    "Popsize",
    "Ngen",
    "Pcross",
    "Pmut",
    "Cost",
    "Time",
    "CrowdingDistance",
    "ExecTimeSec",
]


def migrate_csv_columns(csv_path: Path, fieldnames: List[str]) -> None:
    """Añade columnas faltantes (p. ej. ExecTimeSec) en un CSV ya existente."""
    if not csv_path.exists():
        return
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_fields = list(reader.fieldnames or [])
        rows = list(reader)
    if old_fields == fieldnames:
        return
    for r in rows:
        for fn in fieldnames:
            r.setdefault(fn, "")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({fn: r.get(fn, "") for fn in fieldnames})


def read_existing_unique_keys(csv_path: Path) -> Set[Tuple[str, str]]:
    """Carga un CSV existente y devuelve set de claves (Cost, Time)."""
    if not csv_path.exists():
        return set()
    keys: Set[Tuple[str, str]] = set()
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cost = (r.get("Cost") or "").strip()
            time_val = (r.get("Time") or "").strip()
            if cost and time_val:
                keys.add((cost, time_val))
    return keys


def append_rows(csv_path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta nsga2r varias veces en una instancia y acumula solo soluciones únicas (append)."
    )
    parser.add_argument(
        "--instance",
        required=True,
        type=str,
        help="Ruta a la instancia .txt (ej: instances/instancia_intermedia/instancia_intermedia.txt)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout por ejecución en segundos (default: 600)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="results/unique_solutions_fixed_params",
        help="Carpeta de salida para el CSV acumulado (default: results/unique_solutions_fixed_params)",
    )
    parser.add_argument(
        "--enable-diversity",
        type=int,
        choices=[0, 1],
        default=ENABLE_DIVERSITY,
        help="Init mixta, mutación smart, crowding y búsqueda local: 1=on, 0=off",
    )
    parser.add_argument(
        "--enable-partial-restart",
        type=int,
        choices=[0, 1],
        default=ENABLE_PARTIAL_RESTART,
        help="Reinicio parcial por convergencia: 1=on, 0=off",
    )
    parser.add_argument(
        "--enable-preservation",
        type=int,
        choices=[0, 1],
        default=ENABLE_PRESERVATION,
        help="Archivo externo e inyección periódica: 1=on, 0=off",
    )
    args = parser.parse_args()

    work_dir = Path(__file__).resolve().parent
    project_root = work_dir.parent
    executable = nsga2_executable(project_root)

    instance_path = Path(args.instance).resolve()
    if not instance_path.exists():
        print(f"ERROR: Instancia no encontrada: {instance_path}", file=sys.stderr)
        sys.exit(1)

    if not executable.exists():
        print(f"ERROR: Ejecutable no encontrado: {executable}", file=sys.stderr)
        sys.exit(1)

    output_dir = (project_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pcross_s = fmt_float_for_filename(float(PCROSS))
    pmut_s = fmt_float_for_filename(float(PMUT))
    instance_base = instance_path.stem
    csv_path = output_dir / (
        f"unique_solutions_{instance_base}_pop{POP_SIZE}_ngen{NGEN}_pc{pcross_s}_pm{pmut_s}"
        f"_div{args.enable_diversity}_prest{args.enable_partial_restart}_pres{args.enable_preservation}.csv"
    )

    fieldnames = FIELDNAMES
    migrate_csv_columns(csv_path, fieldnames)

    existing_keys = read_existing_unique_keys(csv_path)
    print("=" * 70)
    print("NSGA-II FIXED PARAMS -> SOLUCIONES UNICAS (append)")
    print("=" * 70)
    print(f"Instancia: {instance_base}")
    print(
        f"Params: popsize={POP_SIZE}, ngen={NGEN}, pcross={PCROSS}, pmut={PMUT}, "
        f"nobj={NOBJ}, enable_diversity={args.enable_diversity}, "
        f"enable_partial_restart={args.enable_partial_restart}, enable_preservation={args.enable_preservation}"
    )
    print(f"Semillas a ejecutar: {SEEDS}")
    print(f"CSV acumulado: {csv_path}")
    print(f"Soluciones únicas ya existentes: {len(existing_keys)}")
    print("=" * 70)

    total_added = 0
    for seed in SEEDS:
        print(f"[seed={seed:.6f}] Ejecutando ...", flush=True)
        success, elapsed, err = run_nsga2_with_timeout(
            executable=executable,
            project_root=project_root,
            seed=float(seed),
            instance_path=instance_path,
            popsize=POP_SIZE,
            ngen=NGEN,
            pcross=float(PCROSS),
            pmut=float(PMUT),
            nobj=NOBJ,
            enable_diversity=int(args.enable_diversity),
            enable_partial_restart=int(args.enable_partial_restart),
            enable_preservation=int(args.enable_preservation),
            timeout_sec=int(args.timeout),
        )
        if not success:
            print(f"[seed={seed:.6f}] FALLÓ ({err}) after {elapsed:.1f}s", flush=True)
            continue

        pareto_solutions, exec_time_sec = parse_pareto_file(instance_path, project_root)
        if not pareto_solutions:
            print(f"[seed={seed:.6f}] Sin CSV Pareto o sin soluciones parseables.", flush=True)
            continue

        if exec_time_sec is None:
            exec_time_sec = elapsed
        exec_time_str = f"{exec_time_sec:.3f}"

        # Deduplicación contra lo ya guardado (Cost,Time).
        rows_to_append: List[Dict[str, str]] = []
        seen_this_run: Set[Tuple[str, str]] = set()
        for sol in pareto_solutions:
            cost = sol["Cost"]
            time_val = sol["Time"]
            key = (cost, time_val)
            if key in existing_keys:
                continue
            if key in seen_this_run:
                continue
            seen_this_run.add(key)

            rows_to_append.append(
                {
                    "Seed": f"{float(seed):.6f}",
                    "Popsize": str(POP_SIZE),
                    "Ngen": str(NGEN),
                    "Pcross": str(PCROSS),
                    "Pmut": str(PMUT),
                    "Cost": cost,
                    "Time": time_val,
                    "CrowdingDistance": sol["CrowdingDistance"],
                    "ExecTimeSec": exec_time_str,
                }
            )
            existing_keys.add(key)

        if rows_to_append:
            append_rows(csv_path, rows_to_append, fieldnames=fieldnames)
            total_added += len(rows_to_append)
            print(
                f"[seed={seed:.6f}] OK. Agregadas {len(rows_to_append)} nuevas soluciones. "
                f"ExecTimeSec={exec_time_str} (wall {elapsed:.1f}s)",
                flush=True,
            )
        else:
            print(
                f"[seed={seed:.6f}] OK. No hubo soluciones nuevas. "
                f"ExecTimeSec={exec_time_str} (wall {elapsed:.1f}s)",
                flush=True,
            )

    print("=" * 70)
    print(f"Listo. Nuevas soluciones agregadas en esta ejecución: {total_added}")
    print("Revisa el CSV acumulado.")
    print("=" * 70)


if __name__ == "__main__":
    main()

