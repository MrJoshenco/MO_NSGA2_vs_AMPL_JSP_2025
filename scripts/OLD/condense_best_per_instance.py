#!/usr/bin/env python3
"""
Condensa los mejores resultados por instancia en un único CSV.
Lee todos los archivos *_best_params_*.csv de una carpeta y los une en
una tabla con una fila por instancia (orden: mayor a menor tamaño).

Uso (desde la raíz del proyecto):
    python3 scripts/condense_best_per_instance.py
    python3 scripts/condense_best_per_instance.py -i results/50runs
    python3 scripts/condense_best_per_instance.py -i results/50runs -t 20260216_234133
"""

import csv
import re
import sys
from pathlib import Path

# Orden típico de instancias (mayor a menor tamaño)
INSTANCE_ORDER = [
    "instancia_gigante",
    "instancia_grande",
    "instancia_intermedia_grande",
    "instancia_intermedia",
    "instancia_basica",
    "instancia_trivial",
]


def find_best_files(results_dir, timestamp=None):
    """
    Busca *_best_params_*.csv en results_dir.
    Si timestamp se da, solo archivos de ese run; si no, usa el más reciente.
    Retorna [(instance_name, path), ...] ordenados por INSTANCE_ORDER.
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        return []
    pattern = re.compile(r"^(.+)_best_params_(\d{8}_\d{6})\.csv$")
    matches = []
    for f in results_path.glob("*_best_params_*.csv"):
        m = pattern.match(f.name)
        if m:
            instance_name, ts = m.group(1), m.group(2)
            if timestamp is None or ts == timestamp:
                matches.append((instance_name, ts, f))
    if not matches:
        return []
    # Usar el timestamp más reciente si no se especificó
    if timestamp is None:
        latest = max(m[1] for m in matches)
        matches = [(name, ts, p) for name, ts, p in matches if ts == latest]
    # Ordenar por INSTANCE_ORDER
    order_map = {n: i for i, n in enumerate(INSTANCE_ORDER)}
    matches.sort(key=lambda x: (order_map.get(x[0], 999), x[0]))
    return [(name, p) for name, _, p in matches]


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Condensar mejores resultados por instancia en un único CSV."
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        default="results/50runs",
        help="Carpeta con *_best_params_*.csv (default: results/50runs)",
    )
    parser.add_argument(
        "-t", "--timestamp",
        type=str,
        default=None,
        help="Timestamp del run a usar (ej: 20260216_234133). Si no se da, usa el más reciente.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Archivo de salida. Por defecto: <input-dir>/best_per_instance_summary_<timestamp>.csv",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    input_dir = project_root / args.input_dir
    files = find_best_files(input_dir, args.timestamp)
    if not files:
        print(f"No se encontraron archivos *_best_params_*.csv en {input_dir}")
        if args.timestamp:
            print(f"con timestamp {args.timestamp}")
        sys.exit(1)

    rows = []
    for instance_name, path in files:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            if row:
                row["Instancia"] = instance_name
                rows.append(row)

    if not rows:
        print("Ningún archivo tenía datos.")
        sys.exit(1)

    out_cols = ["Instancia"] + [c for c in rows[0].keys() if c != "Instancia"]
    timestamp = re.search(r"(\d{8}_\d{6})", str(files[0][1].name))
    ts_str = timestamp.group(1) if timestamp else "summary"
    output_path = Path(args.output) if args.output else input_dir / f"best_per_instance_summary_{ts_str}.csv"
    output_path = output_path if output_path.is_absolute() else project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Condensado: {len(rows)} instancias -> {output_path}")


if __name__ == "__main__":
    main()
