/* Data initializtion routines - IMPROVED VERSION with Greedy and Mixed strategies */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Prototipos locales */
void initialize_ind_random (individual *ind);
void initialize_ind_greedy_cost (individual *ind);
void initialize_ind_greedy_time (individual *ind);
void initialize_ind_greedy_balanced (individual *ind);
void validate_problem_dimensions (void);

/* Variable para controlar si ya se validaron dimensiones */
static int dimensions_validated = 0;

/* Validación de dimensiones (solo una vez) */
void validate_problem_dimensions (void)
{
    if (dimensions_validated) return;
    
    if (nJobs <= 0)
    {
        fprintf(stderr, "\n Error: nJobs debe ser > 0 (valor actual: %d)\n", nJobs);
        exit(1);
    }
    if (nMachines <= 0)
    {
        fprintf(stderr, "\n Error: nMachines debe ser > 0 (valor actual: %d)\n", nMachines);
        exit(1);
    }
    if (nOps <= 0)
    {
        fprintf(stderr, "\n Error: nOps debe ser > 0 (valor actual: %d)\n", nOps);
        exit(1);
    }
    
    dimensions_validated = 1;
}

/* ============================================
   INICIALIZACIÓN DE POBLACIÓN MIXTA
   ============================================
   Estrategia:
   - 20% greedy por costo (extremo del frente Pareto)
   - 20% greedy por tiempo (otro extremo del frente Pareto)
   - 20% greedy balanceado (compromiso costo-tiempo)
   - 40% aleatorio (para diversidad)
*/
void initialize_pop (population *pop)
{
    int i;
    int greedy_cost_end, greedy_time_end, greedy_balanced_end;
    
    validate_problem_dimensions();
    
    /* Calcular límites para cada tipo de inicialización */
    greedy_cost_end = popsize / 5;           /* 20% */
    greedy_time_end = 2 * popsize / 5;       /* 20% más */
    greedy_balanced_end = 3 * popsize / 5;   /* 20% más */
    /* El resto (40%) será aleatorio */
    
    printf("\n Inicializacion mixta: %d greedy-costo, %d greedy-tiempo, %d greedy-balanceado, %d aleatorio",
           greedy_cost_end, 
           greedy_time_end - greedy_cost_end,
           greedy_balanced_end - greedy_time_end,
           popsize - greedy_balanced_end);
    
    /* Greedy por costo (minimizar costo) */
    for (i = 0; i < greedy_cost_end; i++)
    {
        initialize_ind_greedy_cost(&(pop->ind[i]));
    }
    
    /* Greedy por tiempo (minimizar tiempo) */
    for (i = greedy_cost_end; i < greedy_time_end; i++)
    {
        initialize_ind_greedy_time(&(pop->ind[i]));
    }
    
    /* Greedy balanceado (compromiso) */
    for (i = greedy_time_end; i < greedy_balanced_end; i++)
    {
        initialize_ind_greedy_balanced(&(pop->ind[i]));
    }
    
    /* Aleatorio (diversidad) */
    for (i = greedy_balanced_end; i < popsize; i++)
    {
        initialize_ind_random(&(pop->ind[i]));
    }
    
    return;
}

/* Wrapper para mantener compatibilidad */
void initialize_ind (individual *ind)
{
    initialize_ind_random(ind);
    return;
}

/* ============================================
   INICIALIZACIÓN ALEATORIA (original)
   ============================================ */
void initialize_ind_random (individual *ind)
{
    int j, k;

    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            ind->gene[j][k] = rnd(0, nMachines - 1);
        }
    }
    
    return;
}

/* ============================================
   INICIALIZACIÓN GREEDY POR COSTO
   ============================================
   Para cada operación, elegir la máquina con MENOR COSTO.
   Esto genera soluciones en el extremo de mínimo costo del frente Pareto.
*/
void initialize_ind_greedy_cost (individual *ind)
{
    int j, k, m;
    int best_machine;
    double min_cost, current_cost;
    
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            /* Encontrar la máquina con menor costo para esta operación */
            min_cost = ProcessingCost[j][0][k];
            best_machine = 0;
            
            for (m = 1; m < nMachines; m++)
            {
                current_cost = ProcessingCost[j][m][k];
                if (current_cost < min_cost)
                {
                    min_cost = current_cost;
                    best_machine = m;
                }
            }
            
            ind->gene[j][k] = best_machine;
        }
    }
    
    return;
}

/* ============================================
   INICIALIZACIÓN GREEDY POR TIEMPO
   ============================================
   Para cada operación, elegir la máquina con MENOR TIEMPO.
   Esto genera soluciones en el extremo de mínimo tiempo del frente Pareto.
*/
void initialize_ind_greedy_time (individual *ind)
{
    int j, k, m;
    int best_machine;
    double min_time, current_time;
    
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            /* Encontrar la máquina con menor tiempo para esta operación */
            min_time = ProcessingTime[j][0][k];
            best_machine = 0;
            
            for (m = 1; m < nMachines; m++)
            {
                current_time = ProcessingTime[j][m][k];
                if (current_time < min_time)
                {
                    min_time = current_time;
                    best_machine = m;
                }
            }
            
            ind->gene[j][k] = best_machine;
        }
    }
    
    return;
}

/* ============================================
   INICIALIZACIÓN GREEDY BALANCEADA
   ============================================
   Para cada operación, elegir la máquina que minimiza
   una combinación ponderada de costo y tiempo (normalizado).
   Esto genera soluciones en el medio del frente Pareto.
*/
void initialize_ind_greedy_balanced (individual *ind)
{
    int j, k, m;
    int best_machine;
    double best_score, current_score;
    double max_cost, min_cost, max_time, min_time;
    double norm_cost, norm_time;
    
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            /* Primero encontrar max y min para normalización */
            max_cost = min_cost = ProcessingCost[j][0][k];
            max_time = min_time = ProcessingTime[j][0][k];
            
            for (m = 1; m < nMachines; m++)
            {
                if (ProcessingCost[j][m][k] > max_cost) max_cost = ProcessingCost[j][m][k];
                if (ProcessingCost[j][m][k] < min_cost) min_cost = ProcessingCost[j][m][k];
                if (ProcessingTime[j][m][k] > max_time) max_time = ProcessingTime[j][m][k];
                if (ProcessingTime[j][m][k] < min_time) min_time = ProcessingTime[j][m][k];
            }
            
            /* Encontrar la máquina con mejor score balanceado */
            best_machine = 0;
            best_score = 1e30;
            
            for (m = 0; m < nMachines; m++)
            {
                /* Normalizar costo y tiempo al rango [0, 1] */
                if (max_cost > min_cost)
                    norm_cost = (ProcessingCost[j][m][k] - min_cost) / (max_cost - min_cost);
                else
                    norm_cost = 0.0;
                
                if (max_time > min_time)
                    norm_time = (ProcessingTime[j][m][k] - min_time) / (max_time - min_time);
                else
                    norm_time = 0.0;
                
                /* Score balanceado: 50% costo + 50% tiempo */
                current_score = 0.5 * norm_cost + 0.5 * norm_time;
                
                if (current_score < best_score)
                {
                    best_score = current_score;
                    best_machine = m;
                }
            }
            
            ind->gene[j][k] = best_machine;
        }
    }
    
    return;
}

/* ============================================
   ALIAS PARA COMPATIBILIDAD
   ============================================ */
void initialize_pop_mixed (population *pop)
{
    initialize_pop(pop);
}