#!/usr/bin/env python3
"""
NSGA-II Parameter Tuning Script - VERSIÓN MEJORADA
Prueba múltiples instancias (priorizando las más grandes) y exporta resultados
a CSV, ranking ponderado por total_genes, e informe final en Markdown.
Múltiples semillas por (instancia, configuración) para evaluar estabilidad.

Uso (desde la raíz del proyecto):
    python3 scripts/tune_parameters.py          # Búsqueda completa
    python3 scripts/tune_parameters.py --quick  # Búsqueda rápida
"""

import subprocess
import os
import csv
import itertools
import json
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
import glob
import sys
import time as time_module

# ==========================================
# CONFIGURACIÓN DEL EXPERIMENTO
# ==========================================

# Directorio del script (scripts/)
WORK_DIR = os.path.dirname(os.path.abspath(__file__))

# Raíz del proyecto (parent de scripts/)
PROJECT_ROOT = os.path.dirname(WORK_DIR)

# Detectar automáticamente todas las instancias .txt (búsqueda recursiva en instances/)
INSTANCES_DIR = os.path.join(PROJECT_ROOT, "instances")
INSTANCE_PATTERN = "**/instancia*.txt"

# Ejecutable
EXECUTABLE = os.path.join(PROJECT_ROOT, "build", "nsga2r")

# Número de ejecuciones por configuración (para promediar); se sobreescribe con len(SEEDS)
RUNS_PER_CONFIG = 3

# Directorio para resultados (en raíz del proyecto)
RESULTS_DIR = "results/tuning"

# ==========================================
# ESPACIO DE BÚSQUEDA DE PARÁMETROS
# ==========================================

PARAM_GRID_FULL = {
    "popsize": [50, 100, 150, 200],
    "ngen": [100, 200, 300, 500],
    "pcross": [0.7, 0.8, 0.9, 0.95],
    "pmut": [0.01, 0.05, 0.1, 0.15],
}

PARAM_GRID_QUICK = {
    "popsize": [100, 200],
    "ngen": [200, 400],
    "pcross": [0.8, 0.9],
    "pmut": [0.05, 0.1],
}

# Semillas fijas para reproducibilidad (múltiples para estabilidad)
SEEDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_all_instances():
    """Obtiene todas las instancias disponibles ordenadas por tamaño de problema (mayor primero)."""
    instances_dir = Path(INSTANCES_DIR)
    if not instances_dir.exists():
        return []
    paths = list(instances_dir.rglob("instancia*.txt"))
    instances = [str(p) for p in paths]
    # Ordenar por total_genes descendente (instancias grandes primero); si no hay info, por size desc
    def sort_key(path):
        info = get_instance_info(path)
        g = info.get("total_genes") or 0
        if g > 0:
            return (-g, 0)
        return (0, -os.path.getsize(path))
    instances.sort(key=sort_key)
    return instances


def get_instance_info(instance_path):
    """Extrae información básica de la instancia."""
    name = os.path.splitext(os.path.basename(instance_path))[0]
    size = os.path.getsize(instance_path)
    
    # Intentar leer dimensiones del archivo
    # Formato del archivo .txt: primera línea = "nJobs nMachines nOps"
    jobs, machines, ops = 0, 0, 0
    try:
        with open(instance_path, 'r') as f:
            first_line = f.readline().strip()
            parts = first_line.split()
            if len(parts) >= 3:
                jobs = int(parts[0])
                machines = int(parts[1])
                ops = int(parts[2])
    except:
        pass
    
    return {
        "name": name,
        "path": instance_path,
        "size_bytes": size,
        "jobs": jobs,
        "machines": machines,
        "ops": ops,
        "total_genes": jobs * ops if jobs and ops else 0
    }


def nsga2_cmd(
    seed,
    instance,
    popsize,
    ngen,
    nobj,
    pcross,
    pmut,
    enable_diversity=1,
    enable_partial_restart=1,
    enable_preservation=1,
):
    """Construye la línea de comando para nsga2r (switches opcionales al final)."""
    return [
        EXECUTABLE,
        str(seed),
        instance,
        str(popsize),
        str(ngen),
        str(nobj),
        str(pcross),
        str(pmut),
        str(int(bool(enable_diversity))),
        str(int(bool(enable_partial_restart))),
        str(int(bool(enable_preservation))),
    ]


def run_nsga2(
    seed,
    instance,
    popsize,
    ngen,
    nobj,
    pcross,
    pmut,
    enable_diversity=1,
    enable_partial_restart=1,
    enable_preservation=1,
):
    """Ejecuta el algoritmo NSGA-II con los parámetros dados."""
    cmd = nsga2_cmd(
        seed,
        instance,
        popsize,
        ngen,
        nobj,
        pcross,
        pmut,
        enable_diversity=enable_diversity,
        enable_partial_restart=enable_partial_restart,
        enable_preservation=enable_preservation,
    )
    
    try:
        start_time = time_module.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos máximo
            cwd=PROJECT_ROOT
        )
        elapsed = time_module.time() - start_time
        return result.returncode == 0, elapsed
    except subprocess.TimeoutExpired:
        return False, 600
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, 0


def parse_pareto_results(instance_path):
    """Lee el archivo de resultados del frente de Pareto (generado en cwd=PROJECT_ROOT)."""
    base_name = os.path.splitext(os.path.basename(instance_path))[0]
    pareto_file = os.path.join(PROJECT_ROOT, "output", "solutions", f"solutions_{base_name}_pareto.csv")
    
    if not os.path.exists(pareto_file):
        return None
    
    solutions = []
    with open(pareto_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#') or row[0] == 'solucion':
                continue
            try:
                cost = float(row[1])
                time_val = float(row[2])
                solutions.append((cost, time_val))
            except (ValueError, IndexError):
                continue
    
    return solutions


def calculate_metrics(solutions):
    """Calcula métricas de calidad del frente de Pareto."""
    if not solutions:
        return None
    
    costs = [s[0] for s in solutions]
    times = [s[1] for s in solutions]
    unique_solutions = list(set(solutions))
    
    metrics = {
        "best_cost": min(costs),
        "best_time": min(times),
        "worst_cost": max(costs),
        "worst_time": max(times),
        "avg_cost": mean(costs),
        "avg_time": mean(times),
        "total_solutions": len(solutions),
        "unique_solutions": len(unique_solutions),
        "spread_cost": max(costs) - min(costs),
        "spread_time": max(times) - min(times),
    }
    
    # Hypervolume aproximado (punto de referencia normalizado a 1.1 por eje)
    if metrics["spread_cost"] > 0 and metrics["spread_time"] > 0:
        norm_solutions = [
            ((c - metrics["best_cost"]) / metrics["spread_cost"],
             (t - metrics["best_time"]) / metrics["spread_time"])
            for c, t in unique_solutions
        ]
        norm_solutions.sort(key=lambda x: x[0])
        
        hv = 0
        norm_ref = (1.1, 1.1)
        prev_cost = 0
        for nc, nt in norm_solutions:
            if nc < norm_ref[0] and nt < norm_ref[1]:
                width = nc - prev_cost
                height = norm_ref[1] - nt
                hv += width * height
                prev_cost = nc
        hv += (norm_ref[0] - prev_cost) * norm_ref[1]
        metrics["hypervolume"] = hv
        metrics["hv_ref_cost"] = metrics["best_cost"] + norm_ref[0] * metrics["spread_cost"]
        metrics["hv_ref_time"] = metrics["best_time"] + norm_ref[1] * metrics["spread_time"]
    else:
        metrics["hypervolume"] = 0
        metrics["hv_ref_cost"] = 0
        metrics["hv_ref_time"] = 0
    
    return metrics


def calculate_composite_score(metrics, instance_info):
    """Calcula un score compuesto para comparar configuraciones."""
    if not metrics:
        return -float('inf')
    
    # Normalizar según el tamaño de la instancia
    total_genes = instance_info.get("total_genes", 1) or 1
    
    # Ponderaciones
    weights = {
        "best_cost": -0.25,
        "best_time": -0.25,
        "unique_solutions": 0.20,
        "hypervolume": 0.30,
    }
    
    # Normalizar valores relativo al tamaño del problema
    score = 0
    score += weights["best_cost"] * (metrics["best_cost"] / (total_genes * 50))
    score += weights["best_time"] * (metrics["best_time"] / (total_genes * 200))
    score += weights["unique_solutions"] * (metrics["unique_solutions"] / 100)
    score += weights["hypervolume"] * metrics["hypervolume"]
    
    return score


def compute_weighted_global_ranking(all_results, instance_order=None):
    """
    Calcula el ranking global de configuraciones ponderando el score por total_genes
    (priorizando instancias grandes). Retorna lista de dicts con config, score_ponderado, rank.
    """
    if instance_order is None:
        instance_order = sorted(all_results.keys())
    
    # Pesos por instancia: peso_i = total_genes_i / sum(total_genes)
    total_genes_sum = 0
    instance_genes = {}
    for name in instance_order:
        results = all_results.get(name, [])
        g = 0
        if results:
            g = results[0].get("instance_info", {}).get("total_genes") or 0
        instance_genes[name] = max(g, 1)
        total_genes_sum += instance_genes[name]
    
    weights = {name: instance_genes[name] / total_genes_sum for name in instance_order}
    
    # Por cada configuración (clave tuple), recoger score por instancia y calcular ponderado
    config_scores = {}
    for instance_name in instance_order:
        for r in all_results.get(instance_name, []):
            config = r.get("config", {})
            key = (config.get("popsize"), config.get("ngen"), config.get("pcross"), config.get("pmut"))
            if key not in config_scores:
                config_scores[key] = {"config": config, "weighted_score": 0, "scores_by_instance": []}
            s = r.get("score", 0)
            config_scores[key]["weighted_score"] += s * weights[instance_name]
            config_scores[key]["scores_by_instance"].append((instance_name, s))
    
    ranking = []
    for key, data in config_scores.items():
        ranking.append({
            "popsize": key[0],
            "ngen": key[1],
            "pcross": key[2],
            "pmut": key[3],
            "config": data["config"],
            "weighted_score": data["weighted_score"],
            "num_instances": len(data["scores_by_instance"]),
        })
    ranking.sort(key=lambda x: x["weighted_score"], reverse=True)
    for rank, p in enumerate(ranking, 1):
        p["rank_global_ponderado"] = rank
    return ranking, weights


# ==========================================
# EXPORTACIÓN DETALLADA A CSV
# ==========================================

def export_detailed_csv(all_results, timestamp):
    """
    Exporta resultados detallados con UN DATO POR CASILLA.
    Formato apto para Excel/Google Sheets.
    """
    
    results_path = os.path.join(PROJECT_ROOT, RESULTS_DIR)
    
    # === 1. ARCHIVO PRINCIPAL: Todos los resultados ===
    main_file = os.path.join(results_path, f"tuning_all_results_{timestamp}.csv")
    
    with open(main_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        
        # Encabezados - cada uno en su propia columna
        writer.writerow([
            "Instancia",
            "Jobs",
            "Maquinas",
            "Operaciones",
            "Total_Genes",
            "Popsize",
            "Generaciones",
            "P_Cruce",
            "P_Mutacion",
            "Mejor_Costo",
            "Mejor_Costo_STD",
            "Mejor_Tiempo",
            "Mejor_Tiempo_STD",
            "Peor_Costo",
            "Peor_Tiempo",
            "Promedio_Costo",
            "Promedio_Tiempo",
            "Total_Soluciones",
            "Soluciones_Unicas",
            "Spread_Costo",
            "Spread_Tiempo",
            "Hypervolume",
            "Hypervolume_STD",
            "Score_Compuesto",
            "Score_Compuesto_STD",
            "Score_CV",
            "Rank_En_Instancia",
            "Tiempo_Ejecucion_Seg"
        ])
        
        # Datos ordenados por instancia y luego por score
        for instance_name in sorted(all_results.keys()):
            results = all_results[instance_name]
            sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            
            for rank, r in enumerate(sorted_results, 1):
                config = r.get("config", {})
                inst_info = r.get("instance_info", {})
                
                writer.writerow([
                    instance_name,
                    inst_info.get("jobs", ""),
                    inst_info.get("machines", ""),
                    inst_info.get("ops", ""),
                    inst_info.get("total_genes", ""),
                    config.get("popsize", ""),
                    config.get("ngen", ""),
                    config.get("pcross", ""),
                    config.get("pmut", ""),
                    round(r.get("best_cost", 0), 2),
                    round(r.get("best_cost_std", 0), 2),
                    round(r.get("best_time", 0), 2),
                    round(r.get("best_time_std", 0), 2),
                    round(r.get("worst_cost", 0), 2),
                    round(r.get("worst_time", 0), 2),
                    round(r.get("avg_cost", 0), 2),
                    round(r.get("avg_time", 0), 2),
                    int(r.get("total_solutions", 0)),
                    int(r.get("unique_solutions", 0)),
                    round(r.get("spread_cost", 0), 2),
                    round(r.get("spread_time", 0), 2),
                    round(r.get("hypervolume", 0), 4),
                    round(r.get("hypervolume_std", 0), 4),
                    round(r.get("score", 0), 4),
                    round(r.get("score_std", 0), 4),
                    round(r.get("score_cv", 0), 4),
                    rank,
                    round(r.get("exec_time", 0), 2)
                ])
    
    print(f"\n  [CSV] Todos los resultados: {main_file}")
    
    # === 2. ARCHIVO: Mejor configuración por instancia ===
    best_file = os.path.join(results_path, f"tuning_best_per_instance_{timestamp}.csv")
    
    with open(best_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        
        writer.writerow([
            "Instancia",
            "Jobs",
            "Maquinas",
            "Operaciones",
            "Mejor_Popsize",
            "Mejor_Generaciones",
            "Mejor_P_Cruce",
            "Mejor_P_Mutacion",
            "Mejor_Costo_Logrado",
            "Mejor_Tiempo_Logrado",
            "Soluciones_Unicas",
            "Hypervolume",
            "Score"
        ])
        
        for instance_name in sorted(all_results.keys()):
            results = all_results[instance_name]
            if not results:
                continue
            
            best = max(results, key=lambda x: x.get("score", 0))
            config = best.get("config", {})
            inst_info = best.get("instance_info", {})
            
            writer.writerow([
                instance_name,
                inst_info.get("jobs", ""),
                inst_info.get("machines", ""),
                inst_info.get("ops", ""),
                config.get("popsize", ""),
                config.get("ngen", ""),
                config.get("pcross", ""),
                config.get("pmut", ""),
                round(best.get("best_cost", 0), 2),
                round(best.get("best_time", 0), 2),
                int(best.get("unique_solutions", 0)),
                round(best.get("hypervolume", 0), 4),
                round(best.get("score", 0), 4)
            ])
    
    print(f"  [CSV] Mejor por instancia: {best_file}")
    
    # === 3. ARCHIVO: Ranking global de parámetros (con score ponderado por instancias grandes) ===
    params_file = os.path.join(results_path, f"tuning_param_ranking_{timestamp}.csv")
    
    weighted_ranking, _ = compute_weighted_global_ranking(all_results)
    # Map (popsize, ngen, pcross, pmut) -> weighted_score, rank_global_ponderado
    weighted_by_key = {(p["popsize"], p["ngen"], p["pcross"], p["pmut"]): p for p in weighted_ranking}
    
    # Agregar scores por configuración de parámetros
    param_scores = {}
    for instance_name, results in all_results.items():
        for r in results:
            config = r.get("config", {})
            key = (config.get("popsize"), config.get("ngen"), 
                   config.get("pcross"), config.get("pmut"))
            if key not in param_scores:
                param_scores[key] = {"scores": [], "configs": []}
            param_scores[key]["scores"].append(r.get("score", 0))
            param_scores[key]["configs"].append(config)
    
    param_ranking = []
    for key, data in param_scores.items():
        avg_score = mean(data["scores"]) if data["scores"] else 0
        w = weighted_by_key.get(key, {})
        param_ranking.append({
            "popsize": key[0],
            "ngen": key[1],
            "pcross": key[2],
            "pmut": key[3],
            "avg_score": avg_score,
            "num_instances": len(data["scores"]),
            "score_std": stdev(data["scores"]) if len(data["scores"]) > 1 else 0,
            "weighted_score": w.get("weighted_score", 0),
            "rank_global_ponderado": w.get("rank_global_ponderado", 0),
        })
    # Ordenar por score ponderado (configuración general recomendada primero)
    param_ranking.sort(key=lambda x: x["weighted_score"], reverse=True)
    
    with open(params_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        
        writer.writerow([
            "Rank_Global_Ponderado",
            "Popsize",
            "Generaciones",
            "P_Cruce",
            "P_Mutacion",
            "Score_Promedio",
            "Score_STD",
            "Score_Global_Ponderado",
            "Instancias_Probadas"
        ])
        
        for p in param_ranking:
            writer.writerow([
                p["rank_global_ponderado"],
                p["popsize"],
                p["ngen"],
                p["pcross"],
                p["pmut"],
                round(p["avg_score"], 4),
                round(p["score_std"], 4),
                round(p["weighted_score"], 4),
                p["num_instances"]
            ])
    
    print(f"  [CSV] Ranking de parámetros: {params_file}")
    
    # === 4. ARCHIVO: Resumen ejecutivo ===
    summary_file = os.path.join(results_path, f"tuning_summary_{timestamp}.csv")
    
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        
        writer.writerow(["RESUMEN EJECUTIVO DEL TUNING"])
        writer.writerow([])
        writer.writerow(["Metrica", "Valor"])
        writer.writerow(["Fecha", timestamp])
        writer.writerow(["Instancias probadas", len(all_results)])
        writer.writerow(["Configuraciones por instancia", len(param_ranking)])
        writer.writerow(["Ejecuciones por configuracion", RUNS_PER_CONFIG])
        writer.writerow([])
        
        # Mejor configuración global (por score ponderado, priorizando instancias grandes)
        if param_ranking:
            best_global = param_ranking[0]
            writer.writerow(["MEJOR CONFIGURACION GLOBAL (ponderada por total_genes)"])
            writer.writerow(["Parametro", "Valor"])
            writer.writerow(["Popsize", best_global["popsize"]])
            writer.writerow(["Generaciones", best_global["ngen"]])
            writer.writerow(["P_Cruce", best_global["pcross"]])
            writer.writerow(["P_Mutacion", best_global["pmut"]])
            writer.writerow(["Score Promedio", round(best_global["avg_score"], 4)])
            writer.writerow(["Score Global Ponderado", round(best_global["weighted_score"], 4)])
    
    print(f"  [CSV] Resumen ejecutivo: {summary_file}")
    
    return main_file, best_file, params_file, summary_file


def export_json(all_results, timestamp):
    """Exporta todos los resultados en formato JSON."""
    results_path = os.path.join(PROJECT_ROOT, RESULTS_DIR)
    json_file = os.path.join(results_path, f"tuning_full_data_{timestamp}.json")
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"  [JSON] Datos completos: {json_file}")
    return json_file


def generate_informe_final(all_results, best_config, instance_order, timestamp, csv_files=None):
    """
    Genera un informe final en Markdown con objetivo, metodología, resultados
    y recomendaciones. csv_files: dict con main_file, best_file, params_file, summary_file, json_file.
    """
    results_path = os.path.join(PROJECT_ROOT, RESULTS_DIR)
    informe_file = os.path.join(results_path, f"informe_final_{timestamp}.md")
    csv_files = csv_files or {}
    
    lines = []
    lines.append("# Informe final: Sintonización de parámetros NSGA-II")
    lines.append("")
    lines.append(f"**Fecha:** {timestamp}")
    lines.append("")
    lines.append("## Objetivo")
    lines.append("")
    lines.append("Búsqueda de una **configuración general** de parámetros para NSGA-II que funcione bien en todas las instancias, priorizando las instancias más grandes. Evaluación de **estabilidad** mediante múltiples semillas por (instancia, configuración).")
    lines.append("")
    lines.append("## Metodología")
    lines.append("")
    lines.append(f"- **Semillas:** {len(SEEDS)} semillas fijas por (instancia, configuración): `{SEEDS}`")
    lines.append("- **Criterio de score:** Score compuesto (best_cost, best_time, unique_solutions, hypervolume) normalizado por tamaño de instancia.")
    lines.append("- **Configuración general:** Ranking por **score global ponderado**: peso de cada instancia proporcional a `total_genes` (instancias grandes cuentan más).")
    lines.append("- **Estabilidad:** Se reporta media ± desviación estándar y coeficiente de variación (CV) del score entre semillas; CV > 0.2 indica menor estabilidad.")
    lines.append("")
    lines.append("## Instancias (ordenadas de mayor a menor tamaño)")
    lines.append("")
    lines.append("| Instancia | Jobs | Máquinas | Ops | Total genes |")
    lines.append("|-----------|------|----------|-----|-------------|")
    
    for name in instance_order:
        results = all_results.get(name, [])
        if not results:
            continue
        info = results[0].get("instance_info", {})
        lines.append(f"| {name} | {info.get('jobs', '')} | {info.get('machines', '')} | {info.get('ops', '')} | {info.get('total_genes', '')} |")
    
    lines.append("")
    lines.append("## Mejor configuración general")
    lines.append("")
    if best_config:
        cfg = best_config.get("config", best_config)
        lines.append(f"- **popsize:** {cfg.get('popsize')}")
        lines.append(f"- **ngen:** {cfg.get('ngen')}")
        lines.append(f"- **pcross:** {cfg.get('pcross')}")
        lines.append(f"- **pmut:** {cfg.get('pmut')}")
        lines.append(f"- **Score global ponderado:** {best_config.get('weighted_score', 0):.4f}")
        lines.append("")
        lines.append("### Resultados por instancia (mejor configuración)")
        lines.append("")
        lines.append("| Instancia | Mejor costo (media ± std) | Mejor tiempo (media ± std) | Sol. únicas | Hypervolume | Score (media ± std) | CV score |")
        lines.append("|-----------|---------------------------|-----------------------------|-------------|-------------|---------------------|----------|")
        
        for name in instance_order:
            results = all_results.get(name, [])
            r = None
            for x in results:
                c = x.get("config", {})
                if (c.get("popsize"), c.get("ngen"), c.get("pcross"), c.get("pmut")) == (cfg.get("popsize"), cfg.get("ngen"), cfg.get("pcross"), cfg.get("pmut")):
                    r = x
                    break
            if r is None:
                continue
            bc = r.get("best_cost", 0)
            bcs = r.get("best_cost_std", 0)
            bt = r.get("best_time", 0)
            bts = r.get("best_time_std", 0)
            uq = int(r.get("unique_solutions", 0))
            hv = r.get("hypervolume", 0)
            sc = r.get("score", 0)
            scs = r.get("score_std", 0)
            cv = r.get("score_cv", 0)
            lines.append(f"| {name} | {bc:.1f} ± {bcs:.1f} | {bt:.1f} ± {bts:.1f} | {uq} | {hv:.4f} | {sc:.4f} ± {scs:.4f} | {cv:.4f} |")
        
        lines.append("")
        lines.append("### Estabilidad")
        lines.append("")
        cvs = []
        for name in instance_order:
            results = all_results.get(name, [])
            for x in results:
                c = x.get("config", {})
                if (c.get("popsize"), c.get("ngen"), c.get("pcross"), c.get("pmut")) == (cfg.get("popsize"), cfg.get("ngen"), cfg.get("pcross"), cfg.get("pmut")):
                    cvs.append((name, x.get("score_cv", 0)))
                    break
        if cvs:
            max_cv = max(cv for _, cv in cvs)
            lines.append(f"El coeficiente de variación (CV) del score por instancia para la mejor configuración está entre 0 y {max_cv:.4f}. CV &lt; 0.2 se considera estable.")
        lines.append("")
        lines.append("## Recomendación")
        lines.append("")
        lines.append("Ejemplo de ejecución con la configuración recomendada:")
        lines.append("")
        lines.append("```bash")
        lines.append(f"./build/nsga2r 0.5 <archivo_instancia> {cfg.get('popsize')} {cfg.get('ngen')} 2 {cfg.get('pcross')} {cfg.get('pmut')}")
        lines.append("```")
    else:
        lines.append("No se obtuvo ninguna configuración válida.")
    
    lines.append("")
    lines.append("## Archivos generados")
    lines.append("")
    for label, path in csv_files.items():
        if path and os.path.isabs(path):
            path = os.path.relpath(path, results_path)
        lines.append(f"- **{label}:** `{path or '-'}`")
    lines.append("")
    
    content = "\n".join(lines)
    with open(informe_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  [Informe] {informe_file}")
    return informe_file


# ==========================================
# FUNCIÓN PRINCIPAL DE TUNING
# ==========================================

def run_tuning(param_grid, runs_per_config):
    """Ejecuta el tuning con el grid de parámetros especificado."""
    
    global RUNS_PER_CONFIG
    RUNS_PER_CONFIG = runs_per_config
    
    # Crear directorio de resultados
    results_path = os.path.join(PROJECT_ROOT, RESULTS_DIR)
    os.makedirs(results_path, exist_ok=True)
    
    # Obtener todas las instancias
    instances = get_all_instances()
    
    if not instances:
        print("ERROR: No se encontraron instancias (instancia*.txt)")
        return None
    
    instance_order = [get_instance_info(p)["name"] for p in instances]
    
    # Generar todas las combinaciones de parámetros
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    all_combinations = list(itertools.product(*param_values))
    
    total_runs = len(instances) * len(all_combinations) * runs_per_config
    
    print("=" * 70)
    print("NSGA-II PARAMETER TUNING - MULTI-INSTANCE")
    print("=" * 70)
    print(f"Instancias encontradas: {len(instances)}")
    for inst in instances:
        info = get_instance_info(inst)
        print(f"  - {info['name']}: {info['jobs']}x{info['machines']}x{info['ops']} ({info['total_genes']} genes)")
    print(f"Combinaciones de parámetros: {len(all_combinations)}")
    print(f"Ejecuciones por configuración: {runs_per_config}")
    print(f"Total ejecuciones estimadas: {total_runs}")
    print("=" * 70)
    
    # Almacenar todos los resultados por instancia
    all_results = {}
    run_count = 0
    start_total = time_module.time()
    
    # Iterar por cada instancia
    for inst_idx, instance_path in enumerate(instances):
        inst_info = get_instance_info(instance_path)
        instance_name = inst_info["name"]
        
        print(f"\n{'='*70}")
        print(f"INSTANCIA [{inst_idx+1}/{len(instances)}]: {instance_name}")
        print(f"Dimensiones: {inst_info['jobs']} Jobs x {inst_info['machines']} Máquinas x {inst_info['ops']} Ops")
        print(f"{'='*70}")
        
        all_results[instance_name] = []
        
        # Iterar por cada combinación de parámetros
        for combo_idx, combo in enumerate(all_combinations):
            config = dict(zip(param_names, combo))
            
            print(f"\n  [{combo_idx+1}/{len(all_combinations)}] "
                  f"pop={config['popsize']}, gen={config['ngen']}, "
                  f"pc={config['pcross']}, pm={config['pmut']}")
            
            run_metrics = []
            exec_times = []
            
            for run in range(runs_per_config):
                seed = SEEDS[run % len(SEEDS)]
                run_count += 1
                
                progress = (run_count / total_runs) * 100
                print(f"    Run {run+1}/{runs_per_config} (seed={seed}) "
                      f"[{progress:.1f}% total]...", end=" ", flush=True)
                
                success, elapsed = run_nsga2(
                    seed=seed,
                    instance=instance_path,
                    popsize=config["popsize"],
                    ngen=config["ngen"],
                    nobj=2,
                    pcross=config["pcross"],
                    pmut=config["pmut"]
                )
                
                if success:
                    solutions = parse_pareto_results(instance_path)
                    metrics = calculate_metrics(solutions)
                    if metrics:
                        run_metrics.append(metrics)
                        exec_times.append(elapsed)
                        print(f"OK ({elapsed:.1f}s) cost={metrics['best_cost']:.0f}, "
                              f"time={metrics['best_time']:.0f}, unique={metrics['unique_solutions']}")
                    else:
                        print("PARSE_ERROR")
                else:
                    print("FAILED")
            
            # Promediar métricas de todas las ejecuciones y calcular estabilidad (CV del score)
            if run_metrics:
                avg_metrics = {}
                for key in run_metrics[0].keys():
                    values = [m[key] for m in run_metrics]
                    avg_metrics[key] = mean(values)
                    if len(values) > 1:
                        avg_metrics[f"{key}_std"] = stdev(values)
                    else:
                        avg_metrics[f"{key}_std"] = 0
                
                avg_metrics["config"] = config
                avg_metrics["instance_info"] = inst_info
                # Score por run para std y CV
                run_scores = [calculate_composite_score(m, inst_info) for m in run_metrics]
                avg_metrics["score"] = mean(run_scores)
                avg_metrics["score_std"] = stdev(run_scores) if len(run_scores) > 1 else 0
                avg_metrics["score_cv"] = (avg_metrics["score_std"] / abs(avg_metrics["score"])) if avg_metrics["score"] != 0 else 0
                avg_metrics["exec_time"] = mean(exec_times) if exec_times else 0
                
                all_results[instance_name].append(avg_metrics)
    
    elapsed_total = time_module.time() - start_total
    
    # Exportar resultados
    print("\n" + "=" * 70)
    print("EXPORTANDO RESULTADOS")
    print("=" * 70)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    export_detailed_csv(all_results, timestamp)
    json_file = export_json(all_results, timestamp)
    
    # Ranking global ponderado (priorizando instancias grandes)
    weighted_ranking, _ = compute_weighted_global_ranking(all_results, instance_order)
    
    # Mostrar mejores configuraciones globales (por score ponderado)
    print("\n" + "=" * 70)
    print("TOP 5 MEJORES CONFIGURACIONES GLOBALES (score ponderado por instancias grandes)")
    print("=" * 70)
    
    for i, p in enumerate(weighted_ranking[:5], 1):
        print(f"\n#{i} Score ponderado: {p['weighted_score']:.4f}")
        print(f"   Config: pop={p['popsize']}, gen={p['ngen']}, pc={p['pcross']}, pm={p['pmut']}")
    
    # Mostrar mejor por instancia
    print("\n" + "=" * 70)
    print("MEJOR CONFIGURACIÓN POR INSTANCIA")
    print("=" * 70)
    
    for instance_name in sorted(all_results.keys()):
        results = all_results[instance_name]
        if results:
            best = max(results, key=lambda x: x.get("score", 0))
            config = best.get("config", {})
            print(f"\n{instance_name}:")
            print(f"  Config: pop={config['popsize']}, gen={config['ngen']}, "
                  f"pc={config['pcross']}, pm={config['pmut']}")
            print(f"  Mejor Costo: {best['best_cost']:.2f}")
            print(f"  Mejor Tiempo: {best['best_time']:.2f}")
            print(f"  Soluciones únicas: {best['unique_solutions']:.0f}")
    
    # Generar informe final
    results_path = os.path.join(PROJECT_ROOT, RESULTS_DIR)
    best_config = weighted_ranking[0] if weighted_ranking else None
    csv_files = {
        "Todos los resultados": os.path.join(results_path, f"tuning_all_results_{timestamp}.csv"),
        "Mejor por instancia": os.path.join(results_path, f"tuning_best_per_instance_{timestamp}.csv"),
        "Ranking de parámetros": os.path.join(results_path, f"tuning_param_ranking_{timestamp}.csv"),
        "Resumen ejecutivo": os.path.join(results_path, f"tuning_summary_{timestamp}.csv"),
        "Datos completos (JSON)": json_file,
    }
    generate_informe_final(all_results, best_config, instance_order, timestamp, csv_files)
    
    print("\n" + "=" * 70)
    print(f"TUNING COMPLETADO en {elapsed_total/60:.1f} minutos")
    print(f"Resultados guardados en: {os.path.join(PROJECT_ROOT, RESULTS_DIR)}/")
    print("=" * 70)
    
    return all_results


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("\n*** MODO RÁPIDO: Menos combinaciones, resultados más rápidos ***\n")
        run_tuning(PARAM_GRID_QUICK, runs_per_config=len(SEEDS))
    else:
        print("\n*** MODO COMPLETO: Búsqueda exhaustiva (usar --quick para versión rápida) ***\n")
        run_tuning(PARAM_GRID_FULL, runs_per_config=len(SEEDS))
