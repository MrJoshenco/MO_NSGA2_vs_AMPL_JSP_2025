# MO — NSGA-II para MS-FJSSP

Algoritmo evolutivo multiobjetivo (costo y tiempo) para scheduling flexible. El ejecutable principal es `build/nsga2r`.

## Requisitos

- `gcc`, `make`
- Python 3 (opcional, para scripts de experimentos)

## Compilar

Desde la raíz del proyecto:

```bash
make
```

El binario queda en `build/nsga2r`. Para recompilar desde cero:

```bash
make clean && make
```

## Ejecutar

**Siempre desde la raíz del proyecto** (`MO/`), porque las salidas se escriben en `./` y en `output/solutions/`.

```bash
./build/nsga2r <seed> <instancia> <popsize> <ngen> <nobj> <pcross> <pmut> [enable_diversity] [enable_preservation]
```


| Parámetro             | Descripción                               |
| --------------------- | ----------------------------------------- |
| `seed`                | Semilla en `(0, 1)`, p. ej. `0.5`         |
| `instancia`           | Ruta al `.txt` de la instancia            |
| `popsize`             | Tamaño de población (≥ 4 y múltiplo de 4) |
| `ngen`                | Número de generaciones                    |
| `nobj`                | Objetivos (usar `2`)                      |
| `pcross`              | Probabilidad de cruce, p. ej. `0.9`       |
| `pmut`                | Probabilidad de mutación, p. ej. `0.05`   |
| `enable_diversity`    | Opcional: `1` (default) o `0`             |
| `enable_preservation` | Opcional: `1` (default) o `0`             |


### Ejemplo básico

```bash
./build/nsga2r 0.5 instances/basica/instancia_basica.txt 100 200 2 0.9 0.05
```

### Switches de experimentación


| `enable_diversity` | `enable_preservation` | Efecto                                                                                                           |
| ------------------ | --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `1`                | `1`                   | Comportamiento completo (default)                                                                                |
| `0`                | `1`                   | Sin reinicio parcial, sin penalizar duplicados en crowding, init aleatoria, sin búsqueda local ni mutación smart |
| `1`                | `0`                   | Sin archivo externo ni inyección periódica                                                                       |
| `0`                | `0`                   | Ambos mecanismos desactivados                                                                                    |


```bash
# Sin mecanismos de diversidad extra
./build/nsga2r 0.5 instances/basica/instancia_basica.txt 100 200 2 0.9 0.05 0 1
```

Los flags se registran en `params.out`.

## Salidas principales


| Ubicación                                            | Contenido                                            |
| ---------------------------------------------------- | ---------------------------------------------------- |
| `params.out`                                         | Parámetros de la corrida (incluye switches)          |
| `initial_pop.out`, `final_pop.out`, `all_pop.out`    | Poblaciones                                          |
| `output/solutions/solutions_<instancia>_pareto.csv`  | Frente de Pareto (costo, tiempo, crowding; tiempo de corrida en comentario `# exec_time_sec=...`) |
| `output/solutions/solutions_<instancia>_details.csv` | Asignaciones por solución                            |
| `solution_debug.out`                                 | Auditoría y archivo externo (si preservación activa) |


## Scripts Python (opcional)

Desde la raíz:

```bash
# Ajuste de parámetros
python3 scripts/tune_parameters.py

# 50 corridas por instancia
python3 scripts/run_50_per_instance.py

# Acumular soluciones únicas (parámetros fijos en el script)
python3 scripts/test_fixed_params_unique_append.py --instance instances/basica/instancia_basica.txt

# Comparar frentes AMPL/Gurobi vs NSGA-II
python3 scripts/Comparativa\ Pareto/pareto_comparativa.py --batch
```

Los scripts usan `build/nsga2r` y, por defecto, activan diversidad y preservación (`1 1`). En `scripts/tune_parameters.py` está la función `nsga2_cmd(..., enable_diversity=1, enable_preservation=1)` para otras combinaciones.

## Instancias

Las instancias de prueba están en `instances/` (p. ej. `instances/basica/instancia_basica.txt`, `instances/trivial/instancia_trivial.txt`).

## Más información

- Estructura del repo: [ESTRUCTURA.md](ESTRUCTURA.md)
- Detalle del algoritmo: [docs/informe_proyecto.tex](docs/informe_proyecto.tex)

