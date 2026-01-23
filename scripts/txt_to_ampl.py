#!/usr/bin/env python3
"""
Convertidor de formato TXT simple a formato AMPL (.dat)

Formato de entrada (.txt):
    nJobs nMachines nOps
    
    <costos aplanados: Job -> Machine -> Op>
    
    <tiempos aplanados: Job -> Machine -> Op>

Formato de salida (.dat):
    param sigma : (tabla de pesos para objetivos)
    set P := (jobs)
    set M := (máquinas)
    set O := (operaciones)
    param cost := (p m o valor)
    param time_ := (p m o valor)

Uso:
    python txt_to_ampl.py <archivo_entrada.txt> [archivo_salida.dat]
"""

import sys
import os


def read_txt_instance(filepath):
    """Lee una instancia en formato TXT simple."""
    with open(filepath, 'r') as f:
        content = f.read().split()
    
    # Leer dimensiones
    n_jobs = int(content[0])
    n_machines = int(content[1])
    n_ops = int(content[2])
    
    total_values = n_jobs * n_machines * n_ops
    
    # Leer costos (después de las 3 dimensiones)
    costs = []
    for i in range(3, 3 + total_values):
        costs.append(int(float(content[i])))
    
    # Leer tiempos
    times = []
    for i in range(3 + total_values, 3 + 2 * total_values):
        times.append(int(float(content[i])))
    
    return n_jobs, n_machines, n_ops, costs, times


def write_ampl_dat(filepath, n_jobs, n_machines, n_ops, costs, times):
    """Escribe una instancia en formato AMPL .dat"""
    with open(filepath, 'w') as f:
        # 1. Parámetro sigma (tabla de pesos para los objetivos)
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
        
        # 2. Conjuntos P, M, O
        f.write(f"set P := {' '.join(str(i) for i in range(1, n_jobs + 1))};\n")
        f.write(f"set M := {' '.join(str(i) for i in range(1, n_machines + 1))};\n")
        f.write(f"set O := {' '.join(str(i) for i in range(1, n_ops + 1))};\n\n")
        
        # 3. Parámetro cost
        f.write("param cost :=\n")
        f.write("# p m o cost\n")
        write_param_values(f, n_jobs, n_machines, n_ops, costs)
        f.write(";\n\n")
        
        # 4. Parámetro time_
        f.write("param time_ :=\n")
        f.write("# p m o time\n")
        write_param_values(f, n_jobs, n_machines, n_ops, times)
        f.write(";\n")


def write_param_values(f, n_jobs, n_machines, n_ops, values):
    """Escribe los valores de un parámetro en formato AMPL (5 valores por línea)."""
    idx = 0
    count_in_line = 0
    
    for p in range(1, n_jobs + 1):
        for m in range(1, n_machines + 1):
            for o in range(1, n_ops + 1):
                val = values[idx]
                idx += 1
                
                f.write(f"{p} {m} {o} {val}")
                count_in_line += 1
                
                # 5 valores por línea
                if count_in_line >= 5:
                    f.write("\n")
                    count_in_line = 0
                else:
                    f.write("   ")
    
    # Asegurar salto de línea final si la última línea no está completa
    if count_in_line > 0:
        f.write("\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python txt_to_ampl.py <archivo_entrada.txt> [archivo_salida.dat]")
        print("Ejemplo: python txt_to_ampl.py S_instancia.txt instancia_ampl.dat")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Generar nombre de salida si no se proporciona
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.dat"
    
    print(f"Leyendo archivo de entrada: {input_file}")
    n_jobs, n_machines, n_ops, costs, times = read_txt_instance(input_file)
    
    print(f"Dimensiones: {n_jobs} Jobs, {n_machines} Máquinas, {n_ops} Operaciones")
    print(f"Total de valores de costos: {len(costs)}")
    print(f"Total de valores de tiempos: {len(times)}")
    
    print(f"Escribiendo archivo de salida: {output_file}")
    write_ampl_dat(output_file, n_jobs, n_machines, n_ops, costs, times)
    
    print("¡Conversión completada exitosamente!")


if __name__ == "__main__":
    main()
