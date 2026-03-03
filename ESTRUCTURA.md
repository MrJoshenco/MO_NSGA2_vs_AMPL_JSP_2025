# Estructura del proyecto MO

```
MO/
├── src/              # Código fuente C (NSGA-II)
├── build/             # Ejecutable compilado (nsga2r)
├── instances/         # Instancias de entrada
├── scripts/           # Scripts Python (tuning, experimentos, utilidades)
├── docs/              # Documentación del algoritmo
├── output/            # Salidas opcionales (populations/, solutions/)
├── results/           # Resultados de experimentos (unificado)
│   ├── tuning/        # Resultados de tune_parameters.py
│   ├── 50runs/        # Resultados de run_50_per_instance.py
│   ├── testeo_poblacion_variable/
│   ├── testeo_iteraciones_variable/
│   └── testeo_mixto_popsize_ngen/
├── Makefile
└── ESTRUCTURA.md      # Este archivo
```

**Salidas del ejecutable:**  
- En la **raíz**: `*.out`, `params.out`, `solution_debug.out` (poblaciones y parámetros).  
- En **`output/solutions/`**: `solutions_<instancia>_pareto.csv`, `solutions_<instancia>_details.csv`, `solutions_<instancia>_matrix.txt`.  
El binario se ejecuta con `cwd` en la raíz y crea `output/solutions` si no existe. Estos archivos están en `.gitignore` por tamaño.

**Resultados de experimentos:**  
Todos los experimentos (tuning, 50 runs, tests de población/iteraciones/mixto) guardan salidas bajo `results/` en subcarpetas indicadas arriba.
