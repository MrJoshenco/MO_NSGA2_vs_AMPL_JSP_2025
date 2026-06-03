import csv
import argparse
import os

def verificar_soluciones(archivo_instancia, archivo_soluciones):
    # Validar que las rutas existan
    if not os.path.isfile(archivo_instancia):
        print(f"Error: No se encontró el archivo de instancia en la ruta: {archivo_instancia}")
        return
    if not os.path.isfile(archivo_soluciones):
        print(f"Error: No se encontró el archivo de soluciones en la ruta: {archivo_soluciones}")
        return

    # 1. Leer y parsear el archivo de instancia (.txt)
    with open(archivo_instancia, 'r') as f:
        lineas = [linea.strip() for linea in f if linea.strip()]
        
    if not lineas:
        print("Error: El archivo de instancia está vacío.")
        return

    header = lineas[0].split()
    num_jobs = int(header[0])
    num_maquinas = int(header[1])
    num_operaciones = int(header[2])
    
    costos = []
    for i in range(1, num_jobs + 1):
        costos.append([float(x) for x in lineas[i].split()])
        
    tiempos = []
    for i in range(num_jobs + 1, 2 * num_jobs + 1):
        tiempos.append([float(x) for x in lineas[i].split()])
        
    print(f"Instancia cargada: {num_jobs} jobs, {num_maquinas} máquinas, {num_operaciones} operaciones por job.")

    # 2. Leer y agrupar el archivo de soluciones (.csv)
    soluciones = {}
    with open(archivo_soluciones, 'r') as f:
        reader = csv.DictReader(f)
        for fila in reader:
            sol_id = int(fila['solucion'])
            if sol_id not in soluciones:
                soluciones[sol_id] = []
                
            soluciones[sol_id].append({
                'job': int(fila['job']),
                'operacion': int(fila['operacion']),
                'maquina_asignada': int(fila['maquina_asignada']),
                'costo': float(fila['costo']),
                'tiempo': float(fila['tiempo'])
            })

    # 3. Lógica de validación
    todas_validas = True
    soluciones_con_errores = 0

    print("Iniciando verificación de soluciones...\n")
    print("-" * 50)

    for sol_id, asignaciones in soluciones.items():
        es_valida = True
        errores = []
        
        asignaciones_esperadas = num_jobs * num_operaciones
        if len(asignaciones) != asignaciones_esperadas:
            errores.append(f"Cantidad incorrecta de asignaciones. Esperado: {asignaciones_esperadas}, Actual: {len(asignaciones)}")
            es_valida = False
            
        for asig in asignaciones:
            j = asig['job']
            o = asig['operacion']
            m = asig['maquina_asignada']
            costo_csv = asig['costo']
            tiempo_csv = asig['tiempo']
            
            if not (1 <= j <= num_jobs) or not (1 <= o <= num_operaciones) or not (1 <= m <= num_maquinas):
                errores.append(f"Índices fuera de rango detectados en Job {j}, Op {o}, Máquina {m}.")
                es_valida = False
                continue
                
            col_idx = (m - 1) * num_operaciones + (o - 1)
            row_idx = j - 1
            
            costo_esperado = costos[row_idx][col_idx]
            tiempo_esperado = tiempos[row_idx][col_idx]
            
            if abs(costo_esperado - costo_csv) > 1e-4:
                errores.append(f"Costo incorrecto (Job {j}, Op {o}, Maq {m}): CSV={costo_csv} | Esperado={costo_esperado}")
                es_valida = False
                
            if abs(tiempo_esperado - tiempo_csv) > 1e-4:
                errores.append(f"Tiempo incorrecto (Job {j}, Op {o}, Maq {m}): CSV={tiempo_csv} | Esperado={tiempo_esperado}")
                es_valida = False
                
        if not es_valida:
            print(f"Solución {sol_id} es INVÁLIDA:")
            for err in errores[:5]:
                print(f"    - {err}")
            if len(errores) > 5:
                print(f"    ... y {len(errores) - 5} errores más.")
            todas_validas = False
            soluciones_con_errores += 1

    # 4. Resumen Final
    print("-" * 50)
    if todas_validas:
        print(f"Las {len(soluciones)} soluciones revisadas son completamente consistentes con la matriz de la instancia.")
    else:
        print(f"Se encontraron discrepancias en {soluciones_con_errores} de las {len(soluciones)} soluciones.")

if __name__ == "__main__":
    # Configuración de argumentos por línea de comandos
    parser = argparse.ArgumentParser(description="Verifica las soluciones contra los parámetros de la instancia.")
    
    # Argumentos requeridos para las rutas de los archivos
    
    #   instances/basica/instancia_basica.txt
    #   output/solutions/solutions_instancia_basica_details.csv
    
    #   instances/intermedia/instancia_intermedia.txt
    #   output/solutions/solutions_instancia_intermedia_details.csv
    
    #   instances/intermedia_grande/instancia_intermedia_grande.txt
    #   output/solutions/solutions_instancia_intermedia_grande_details.csv
    

    #   instances/grande/instancia_grande.txt
    #   output/solutions/solutions_instancia_grande_details.csv

    #   instances/gigante/instancia_gigante.txt
    #   output/solutions/solutions_instancia_gigante_details.csv

    parser.add_argument("-i", "--instancia", required=True, help="Ruta absoluta o relativa al archivo .txt de la instancia")
    parser.add_argument("-s", "--soluciones", required=True, help="Ruta absoluta o relativa al archivo .csv de las soluciones")
    
    args = parser.parse_args()
    
    # Ejecutar la verificación con las rutas provistas
    verificar_soluciones(args.instancia, args.soluciones)