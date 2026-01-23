#!/usr/bin/env python3
"""
Generador de instancias de prueba de diferentes tamaños.
Genera archivos en formato TXT simple y opcionalmente en formato AMPL .dat
"""

import random
import os

# Configuración de las instancias
INSTANCIAS = [
    {
        "nombre": "instancia_trivial",
        "jobs": 2,
        "machines": 2,
        "ops": 2,
        "descripcion": "Casi trivial (2x2x2 = 8 asignaciones)"
    },
    {
        "nombre": "instancia_basica",
        "jobs": 4,
        "machines": 3,
        "ops": 3,
        "descripcion": "Básica (4x3x3 = 36 asignaciones)"
    },
    {
        "nombre": "instancia_intermedia",
        "jobs": 10,
        "machines": 6,
        "ops": 6,
        "descripcion": "Intermedia (10x6x6 = 360 asignaciones)"
    },
    {
        "nombre": "instancia_grande",
        "jobs": 30,
        "machines": 15,
        "ops": 15,
        "descripcion": "Grande (30x15x15 = 6,750 asignaciones)"
    },
    {
        "nombre": "instancia_gigante",
        "jobs": 50,
        "machines": 20,
        "ops": 20,
        "descripcion": "Gigante (50x20x20 = 20,000 asignaciones)"
    }
]

# Rangos para valores aleatorios
COST_MIN, COST_MAX = 5, 50
TIME_MIN, TIME_MAX = 10, 200


def generate_txt_instance(filepath, num_jobs, num_machines, num_ops):
    """Genera una instancia en formato TXT simple."""
    with open(filepath, 'w') as f:
        # Cabecera: dimensiones
        f.write(f"{num_jobs} {num_machines} {num_ops}\n\n")
        
        # Matriz de Costos
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    val = random.randint(COST_MIN, COST_MAX)
                    f.write(f"{val} ")
            f.write("\n")
        
        f.write("\n")
        
        # Matriz de Tiempos
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    val = random.randint(TIME_MIN, TIME_MAX)
                    f.write(f"{val} ")
            f.write("\n")


def generate_ampl_dat(filepath, num_jobs, num_machines, num_ops, costs, times):
    """Genera una instancia en formato AMPL .dat"""
    with open(filepath, 'w') as f:
        # Parámetro sigma
        f.write("param sigma :\n")
        f.write("    1       2 :=\n")
        sigma_values = [
            ("0.00001", "0.99999"),
            ("0.1", "0.9"),
            ("0.2", "0.8"),
            ("0.3", "0.7"),
            ("0.4", "0.6"),
            ("0.5", "0.5"),
            ("0.6", "0.4"),
            ("0.7", "0.3"),
            ("0.8", "0.2"),
            ("0.9", "0.1"),
            ("0.99999", "0.00001")
        ]
        for i, (s1, s2) in enumerate(sigma_values, start=1):
            f.write(f"{i}   {s1} {s2}\n")
        f.write(";\n\n")
        
        # Conjuntos
        f.write(f"set P := {' '.join(str(i) for i in range(1, num_jobs + 1))};\n")
        f.write(f"set M := {' '.join(str(i) for i in range(1, num_machines + 1))};\n")
        f.write(f"set O := {' '.join(str(i) for i in range(1, num_ops + 1))};\n\n")
        
        # Costos
        f.write("param cost :=\n")
        f.write("# p m o cost\n")
        write_param_values(f, num_jobs, num_machines, num_ops, costs)
        f.write(";\n\n")
        
        # Tiempos
        f.write("param time_ :=\n")
        f.write("# p m o time\n")
        write_param_values(f, num_jobs, num_machines, num_ops, times)
        f.write(";\n")


def write_param_values(f, num_jobs, num_machines, num_ops, values):
    """Escribe los valores de un parámetro en formato AMPL."""
    idx = 0
    count_in_line = 0
    
    for p in range(1, num_jobs + 1):
        for m in range(1, num_machines + 1):
            for o in range(1, num_ops + 1):
                val = values[idx]
                idx += 1
                
                f.write(f"{p} {m} {o} {val}")
                count_in_line += 1
                
                if count_in_line >= 5:
                    f.write("\n")
                    count_in_line = 0
                else:
                    f.write("   ")
    
    if count_in_line > 0:
        f.write("\n")


def generate_both_formats(base_dir, nombre, num_jobs, num_machines, num_ops):
    """Genera ambos formatos (TXT y DAT) para una instancia."""
    random.seed()  # Reiniciar semilla para cada instancia
    
    total = num_jobs * num_machines * num_ops
    
    # Generar valores aleatorios
    costs = [random.randint(COST_MIN, COST_MAX) for _ in range(total)]
    times = [random.randint(TIME_MIN, TIME_MAX) for _ in range(total)]
    
    # Generar TXT
    txt_path = os.path.join(base_dir, f"{nombre}.txt")
    with open(txt_path, 'w') as f:
        f.write(f"{num_jobs} {num_machines} {num_ops}\n\n")
        
        idx = 0
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    f.write(f"{costs[idx]} ")
                    idx += 1
            f.write("\n")
        
        f.write("\n")
        
        idx = 0
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    f.write(f"{times[idx]} ")
                    idx += 1
            f.write("\n")
    
    # Generar DAT
    dat_path = os.path.join(base_dir, f"{nombre}.dat")
    generate_ampl_dat(dat_path, num_jobs, num_machines, num_ops, costs, times)
    
    return txt_path, dat_path


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("GENERADOR DE INSTANCIAS DE PRUEBA")
    print("=" * 60)
    
    for inst in INSTANCIAS:
        nombre = inst["nombre"]
        jobs = inst["jobs"]
        machines = inst["machines"]
        ops = inst["ops"]
        desc = inst["descripcion"]
        total = jobs * machines * ops
        
        print(f"\n📁 Generando: {nombre}")
        print(f"   {desc}")
        print(f"   Dimensiones: {jobs} Jobs × {machines} Máquinas × {ops} Operaciones")
        
        txt_path, dat_path = generate_both_formats(base_dir, nombre, jobs, machines, ops)
        
        # Mostrar tamaños de archivo
        txt_size = os.path.getsize(txt_path)
        dat_size = os.path.getsize(dat_path)
        
        print(f"   ✓ {nombre}.txt ({txt_size:,} bytes)")
        print(f"   ✓ {nombre}.dat ({dat_size:,} bytes)")
    
    print("\n" + "=" * 60)
    print("¡GENERACIÓN COMPLETADA!")
    print("=" * 60)
    
    print("\n📊 Resumen de archivos generados:")
    print("-" * 60)
    print(f"{'Instancia':<25} {'Jobs':<6} {'Maq':<6} {'Ops':<6} {'Total':<10}")
    print("-" * 60)
    for inst in INSTANCIAS:
        nombre = inst["nombre"]
        j, m, o = inst["jobs"], inst["machines"], inst["ops"]
        total = j * m * o
        print(f"{nombre:<25} {j:<6} {m:<6} {o:<6} {total:<10,}")
    print("-" * 60)
    
    print("\n🚀 Para ejecutar el algoritmo con una instancia:")
    print("   ./nsga2r 0.5 instancia_basica.txt 100 200 2 0.9 0.05")


if __name__ == "__main__":
    main()
