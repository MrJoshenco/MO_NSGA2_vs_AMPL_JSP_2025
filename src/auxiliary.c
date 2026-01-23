/* Some utility functions (not part of the algorithm) */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Function to return the maximum of two variables */
double maximum (double a, double b)
{
    if (a>b)
    {
        return(a);
    }
    return (b);
}

/* Function to return the minimum of two variables */
double minimum (double a, double b)
{
    if (a<b)
    {
        return (a);
    }
    return (b);
}

/* Function to check if two individuals have identical genes */
int are_genes_equal (individual *ind1, individual *ind2)
{
    int j, k;
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            if (ind1->gene[j][k] != ind2->gene[j][k])
            {
                return 0;  /* Different */
            }
        }
    }
    return 1;  /* Equal */
}

/* Function to check if two individuals have identical objective values */
int are_objectives_equal (individual *ind1, individual *ind2)
{
    int i;
    for (i = 0; i < nobj; i++)
    {
        if (fabs(ind1->obj[i] - ind2->obj[i]) > EPS)
        {
            return 0;  /* Different */
        }
    }
    return 1;  /* Equal */
}

/* ============================================
   BÚSQUEDA LOCAL (HILL CLIMBING)
   ============================================
   Mejora un individuo probando cambios locales en cada gen.
   Se enfoca en mejorar un objetivo específico o un balance de ambos.
*/

/* Búsqueda local enfocada en minimizar COSTO */
void local_search_cost (individual *ind)
{
    int j, k, m;
    int current_machine, best_machine;
    double current_cost, best_cost;
    int improved = 1;
    int max_iterations = 3;  /* Limitar iteraciones para eficiencia */
    int iteration = 0;
    
    while (improved && iteration < max_iterations)
    {
        improved = 0;
        iteration++;
        
        for (j = 0; j < nJobs; j++)
        {
            for (k = 0; k < nOps; k++)
            {
                current_machine = ind->gene[j][k];
                best_machine = current_machine;
                best_cost = ProcessingCost[j][current_machine][k];
                
                /* Probar cada máquina alternativa */
                for (m = 0; m < nMachines; m++)
                {
                    if (m == current_machine) continue;
                    
                    current_cost = ProcessingCost[j][m][k];
                    
                    if (current_cost < best_cost)
                    {
                        best_cost = current_cost;
                        best_machine = m;
                        improved = 1;
                    }
                }
                
                ind->gene[j][k] = best_machine;
            }
        }
    }
}

/* Búsqueda local enfocada en minimizar TIEMPO */
void local_search_time (individual *ind)
{
    int j, k, m;
    int current_machine, best_machine;
    double current_time, best_time;
    int improved = 1;
    int max_iterations = 3;
    int iteration = 0;
    
    while (improved && iteration < max_iterations)
    {
        improved = 0;
        iteration++;
        
        for (j = 0; j < nJobs; j++)
        {
            for (k = 0; k < nOps; k++)
            {
                current_machine = ind->gene[j][k];
                best_machine = current_machine;
                best_time = ProcessingTime[j][current_machine][k];
                
                for (m = 0; m < nMachines; m++)
                {
                    if (m == current_machine) continue;
                    
                    current_time = ProcessingTime[j][m][k];
                    
                    if (current_time < best_time)
                    {
                        best_time = current_time;
                        best_machine = m;
                        improved = 1;
                    }
                }
                
                ind->gene[j][k] = best_machine;
            }
        }
    }
}

/* Búsqueda local BALANCEADA (mejora ambos objetivos con pesos) */
void local_search_balanced (individual *ind, double weight_cost, double weight_time)
{
    int j, k, m;
    int current_machine, best_machine;
    double current_score, best_score;
    int improved = 1;
    int max_iterations = 2;
    int iteration = 0;
    
    /* Normalización aproximada basada en escalas típicas */
    double scale_cost = 1.0;
    double scale_time = 1.0;
    
    /* Estimar escalas a partir del primer job/op para normalización */
    if (nJobs > 0 && nOps > 0 && nMachines > 0)
    {
        double avg_cost = 0, avg_time = 0;
        int count = 0;
        for (m = 0; m < nMachines; m++)
        {
            avg_cost += ProcessingCost[0][m][0];
            avg_time += ProcessingTime[0][m][0];
            count++;
        }
        if (count > 0)
        {
            scale_cost = avg_cost / count;
            scale_time = avg_time / count;
            if (scale_cost < 1.0) scale_cost = 1.0;
            if (scale_time < 1.0) scale_time = 1.0;
        }
    }
    
    while (improved && iteration < max_iterations)
    {
        improved = 0;
        iteration++;
        
        for (j = 0; j < nJobs; j++)
        {
            for (k = 0; k < nOps; k++)
            {
                current_machine = ind->gene[j][k];
                best_machine = current_machine;
                best_score = (weight_cost * ProcessingCost[j][current_machine][k] / scale_cost) +
                             (weight_time * ProcessingTime[j][current_machine][k] / scale_time);
                
                for (m = 0; m < nMachines; m++)
                {
                    if (m == current_machine) continue;
                    
                    current_score = (weight_cost * ProcessingCost[j][m][k] / scale_cost) +
                                    (weight_time * ProcessingTime[j][m][k] / scale_time);
                    
                    if (current_score < best_score)
                    {
                        best_score = current_score;
                        best_machine = m;
                        improved = 1;
                    }
                }
                
                ind->gene[j][k] = best_machine;
            }
        }
    }
}

/* Aplicar búsqueda local a las mejores soluciones de una población */
void apply_local_search_to_best (population *pop, int num_to_improve)
{
    int i;
    int improved_count = 0;
    
    /* Aplicar búsqueda local solo a soluciones del frente Pareto (rank=1) */
    for (i = 0; i < popsize && improved_count < num_to_improve; i++)
    {
        if (pop->ind[i].rank == 1)
        {
            /* Alternar entre diferentes tipos de búsqueda local */
            switch (improved_count % 3)
            {
                case 0:
                    local_search_cost(&(pop->ind[i]));
                    break;
                case 1:
                    local_search_time(&(pop->ind[i]));
                    break;
                case 2:
                    local_search_balanced(&(pop->ind[i]), 0.5, 0.5);
                    break;
            }
            improved_count++;
        }
    }
}
