/* Crossover routines - IMPROVED VERSION with multiple crossover types */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Prototipos locales */
void scheduler_cross_uniform (individual *parent1, individual *parent2, individual *child1, individual *child2);
void scheduler_cross_twopoint (individual *parent1, individual *parent2, individual *child1, individual *child2);
void copy_parents_to_children (individual *parent1, individual *parent2, individual *child1, individual *child2);

/* Function to cross two individuals - HYBRID approach */
void crossover (individual *parent1, individual *parent2, individual *child1, individual *child2)
{
    /* Alternar entre diferentes tipos de cruce para mejor exploración */
    /* 60% Two-Point (preserva bloques), 40% Uniform (más exploración) */
    if (randomperc() <= 0.6)
    {
        scheduler_cross_twopoint(parent1, parent2, child1, child2);
    }
    else
    {
        scheduler_cross_uniform(parent1, parent2, child1, child2);
    }
    return;
}

/* Helper: Copiar padres a hijos (sin cruce) */
void copy_parents_to_children (individual *parent1, individual *parent2, individual *child1, individual *child2)
{
    int j, k;
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            child1->gene[j][k] = parent1->gene[j][k];
            child2->gene[j][k] = parent2->gene[j][k];
        }
    }
}

/* ============================================
   CRUCE TWO-POINT POR JOBS
   ============================================
   Selecciona dos puntos de cruce a nivel de Jobs.
   Los jobs entre los puntos se intercambian completamente.
   Esto preserva bloques de asignaciones que funcionan bien juntas.
*/
void scheduler_cross_twopoint (individual *parent1, individual *parent2, individual *child1, individual *child2)
{
    int j, k;
    int point1, point2, temp;
    
    /* Verificar probabilidad de cruce */
    if (randomperc() > pcross_bin)
    {
        copy_parents_to_children(parent1, parent2, child1, child2);
        return;
    }
    
    nbincross++;
    
    /* Seleccionar dos puntos de cruce (a nivel de Jobs) */
    point1 = rnd(0, nJobs - 1);
    point2 = rnd(0, nJobs - 1);
    
    /* Asegurar que point1 < point2 */
    if (point1 > point2) 
    { 
        temp = point1; 
        point1 = point2; 
        point2 = temp; 
    }
    
    /* Realizar el cruce */
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            if (j >= point1 && j <= point2)
            {
                /* Zona de intercambio: jobs entre point1 y point2 */
                child1->gene[j][k] = parent2->gene[j][k];
                child2->gene[j][k] = parent1->gene[j][k];
            }
            else
            {
                /* Fuera de zona: mantener del padre original */
                child1->gene[j][k] = parent1->gene[j][k];
                child2->gene[j][k] = parent2->gene[j][k];
            }
        }
    }
    
    return;
}

/* ============================================
   CRUCE UNIFORME (original mejorado)
   ============================================
   Cada gen tiene 50% probabilidad de venir de cada padre.
   Bueno para exploración pero puede romper estructuras buenas.
*/
void scheduler_cross_uniform (individual *parent1, individual *parent2, individual *child1, individual *child2)
{
    int j, k;
    
    /* Verificar probabilidad de cruce */
    if (randomperc() > pcross_bin)
    {
        copy_parents_to_children(parent1, parent2, child1, child2);
        return;
    }
    
    nbincross++;
    
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            /* Cruce Uniforme: 50% probabilidad de heredar de P1 o P2 */
            if (randomperc() <= 0.5)
            {
                child1->gene[j][k] = parent1->gene[j][k];
                child2->gene[j][k] = parent2->gene[j][k];
            }
            else
            {
                child1->gene[j][k] = parent2->gene[j][k];
                child2->gene[j][k] = parent1->gene[j][k];
            }
        }
    }
    
    return;
}

/* Mantener función legacy para compatibilidad */
void scheduler_cross (individual *parent1, individual *parent2, individual *child1, individual *child2)
{
    scheduler_cross_twopoint(parent1, parent2, child1, child2);
}