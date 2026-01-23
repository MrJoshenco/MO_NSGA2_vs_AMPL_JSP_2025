import random

# ================= CONFIGURACIÓN =================
# Ajusta estos valores para cambiar el tamaño del problema
NUM_JOBS = 3        # Cantidad de Trabajos (P)
NUM_MACHINES = 4    # Cantidad de Máquinas (M)
NUM_OPS = 3        # Cantidad de Operaciones (O)

# Nombre del archivo de salida (usamos .txt para denotar que es simple)
FILENAME = "S_instancia.txt"
# =================================================

def generate_simple_instance(filename, num_jobs, num_machines, num_ops):
    print(f"Generando instancia SIMPLE: {num_jobs} Jobs, {num_machines} Máquinas, {num_ops} Operaciones...")
    
    with open(filename, 'w') as f:
        # 1. Cabecera: Dimensiones
        # El lector C espera: "%d %d %d"
        f.write(f"{num_jobs} {num_machines} {num_ops}\n")
        f.write("\n")

        # 2. Matriz de Costos (Flattened/Aplanada)
        # El lector C lee en orden: Job -> Machine -> Op
        print("Generando matriz de Costos...")
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    val = random.randint(5, 50)
                    f.write(f"{val} ")
            f.write("\n") # Salto de línea por Job para legibilidad humana (C lo ignora)
        
        f.write("\n")

        # 3. Matriz de Tiempos (Flattened/Aplanada)
        print("Generando matriz de Tiempos...")
        for p in range(num_jobs):
            for m in range(num_machines):
                for o in range(num_ops):
                    val = random.randint(10, 200)
                    f.write(f"{val} ")
            f.write("\n") # Salto de línea por Job

    print(f"¡Éxito! Archivo '{filename}' generado correctamente.")
    print(f"Formato: 3 enteros iniciales, seguidos de {num_jobs*num_machines*num_ops} costos y {num_jobs*num_machines*num_ops} tiempos.")

if __name__ == "__main__":
    generate_simple_instance(FILENAME, NUM_JOBS, NUM_MACHINES, NUM_OPS)