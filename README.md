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


# Acumular soluciones únicas (parámetros fijos en el script)
python3 scripts/test_fixed_params_unique_append.py --instance instances/basica/instancia_basica.txt

# Comparar frentes AMPL/Gurobi vs NSGA-II
python3 scripts/Comparativa\ Pareto/pareto_comparativa.py --batch
```

`test_fixed_params_unique_append.py` acepta opciones adicionales:

```bash
python3 scripts/test_fixed_params_unique_append.py \
  --instance instances/basica/instancia_basica.txt \
  --enable-diversity 0 \
  --enable-preservation 1 \
  --timeout 600 \
  -o results/unique_solutions_fixed_params
```

Parámetros fijos usados en el script (actualmente):
- `popsize=1000`
- `ngen=4000`
- `pcross=0.9`
- `pmut=0.01`
- `nobj=2`

Salida por defecto:
- `results/unique_solutions_fixed_params/`
- nombre de archivo: `unique_solutions_<instancia>_pop<POP_SIZE>_ngen<NGEN>_pc<PCROSS>_pm<PMUT>_div<enable_diversity>_pres<enable_preservation>.csv`

Los scripts usan `build/nsga2r` y, por defecto, activan diversidad y preservación (`1 1`). En `scripts/tune_parameters.py` está la función `nsga2_cmd(..., enable_diversity=1, enable_preservation=1)` para otras combinaciones.

## Instancias

Las instancias de prueba están en `instances/`. La estructura actual incluye carpetas como:

- `instances/basica/instancia_basica.txt`
- `instances/trivial/instancia_trivial.txt`
- `instances/intermedia/instancia_intermedia.txt`
- `instances/intermedia_grande/instancia_intermedia_grande.txt`
- `instances/grande/instancia_grande.txt`
- `instances/gigante/instancia_gigante.txt`
- `instances/mega_gigante/instancia_mega_gigante.txt`
- `instances/otras/gran_instancia.txt`
- `instances/otras/S_instancia.txt`

Usa la ruta completa del archivo `.txt` como valor de `--instance` para los scripts y para `build/nsga2r`.

## Más información

- Estructura del repo: [ESTRUCTURA.md](ESTRUCTURA.md)
- Detalle del algoritmo: [docs/informe_proyecto.tex](docs/informe_proyecto.tex)

