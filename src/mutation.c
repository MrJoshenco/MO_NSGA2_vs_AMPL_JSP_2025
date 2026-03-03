/* Mutation routines - INTELLIGENT HYBRID ADAPTIVE VERSION */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Prototipos locales */
void scheduler_mutate_hybrid (individual *ind);
void scheduler_mutate_smart (individual *ind);
void mutate_single_gene (individual *ind, int job, int op);
void mutate_single_gene_smart (individual *ind, int job, int op);
void mutate_entire_job (individual *ind, int job);

/* Parámetros de mutación híbrida (ajustables) */
#define TARGET_FINE_MUTATIONS 2.0    /* Mutaciones finas esperadas por individuo */
#define PROB_BLOCK_MUTATION 0.05     /* Probabilidad de mutar un job completo */
#define MIN_PMUT 0.001               /* Probabilidad mínima de mutación por gen */
#define MAX_PMUT 0.3                 /* Probabilidad máxima de mutación por gen */
#define PROB_SMART_MUTATION 0.2      /* Reducido de 0.5: demasiada smart mutation sesga la búsqueda */


/* Function to perform mutation in a population - INTELLIGENT VERSION */
void mutation_pop (population *pop)
{
    int i;
    for (i = 0; i < popsize; i++)
    {
        /* Alternar entre mutación inteligente y híbrida */
        /* 50% inteligente (mejora dirigida), 50% híbrida (exploración) */
        if (randomperc() <= PROB_SMART_MUTATION)
        {
            scheduler_mutate_smart(&(pop->ind[i]));
        }
        else
        {
            scheduler_mutate_hybrid(&(pop->ind[i]));
        }
    }
    return;
}

/* Function to perform mutation of an individual */
void mutation_ind (individual *ind)
{
    scheduler_mutate_hybrid(ind);
    return;
}

/* Helper: Mutar un solo gen (una operación de un job) */
void mutate_single_gene (individual *ind, int job, int op)
{
    int old_machine, new_machine;
    
    if (nMachines <= 1) return;  /* No hay alternativa */
    
    old_machine = ind->gene[job][op];
    do {
        new_machine = rnd(0, nMachines - 1);
    } while (new_machine == old_machine);
    
    ind->gene[job][op] = new_machine;
    nbinmut++;
}

/* Helper: Mutar todas las operaciones de un job completo */
void mutate_entire_job (individual *ind, int job)
{
    int k;
    
    if (nMachines <= 1) return;  /* No hay alternativa */
    
    for (k = 0; k < nOps; k++)
    {
        /* Asignar nueva máquina aleatoria (puede ser igual o diferente) */
        ind->gene[job][k] = rnd(0, nMachines - 1);
        nbinmut++;
    }
}

/* MUTACIÓN HÍBRIDA ADAPTATIVA
   Combina:
   1. Mutación FINA: pocos genes individuales (adaptativo al tamaño)
   2. Mutación GRUESA: ocasionalmente muta jobs completos
   
   Esto permite:
   - Refinamiento local (mutación fina)
   - Escape de óptimos locales (mutación gruesa)
   - Escalabilidad a cromosomas grandes
*/
void scheduler_mutate_hybrid (individual *ind)
{
    int j, k;
    int total_genes;
    double pmut_fine;
    
    /* ============================================ */
    /* PARTE 1: MUTACIÓN FINA (adaptativa al tamaño) */
    /* ============================================ */
    
    total_genes = nJobs * nOps;
    
    /* Usar el máximo entre la tasa adaptativa y la especificada por el usuario */
    pmut_fine = TARGET_FINE_MUTATIONS / (double)total_genes;
    
    if (pmut_fine < MIN_PMUT) pmut_fine = MIN_PMUT;
    if (pmut_fine > MAX_PMUT) pmut_fine = MAX_PMUT;
    
    if (pmut_bin > pmut_fine)
    {
        pmut_fine = pmut_bin;
    }
    
    /* Aplicar mutación fina gen por gen */
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            if (randomperc() <= pmut_fine)
            {
                mutate_single_gene(ind, j, k);
            }
        }
    }
    
    /* ============================================ */
    /* PARTE 2: MUTACIÓN GRUESA (por bloques/jobs)  */
    /* ============================================ */
    
    /* Ocasionalmente mutar un job completo para exploración agresiva */
    for (j = 0; j < nJobs; j++)
    {
        if (randomperc() <= PROB_BLOCK_MUTATION)
        {
            mutate_entire_job(ind, j);
        }
    }
    
    return;
}

/* ============================================
   MUTACIÓN INTELIGENTE (SMART MUTATION)
   ============================================
   En lugar de mutar aleatoriamente, busca máquinas que
   mejoren los objetivos. Tiene una pequeña probabilidad
   de aceptar peores opciones para mantener diversidad.
*/
void mutate_single_gene_smart (individual *ind, int job, int op)
{
    int m;
    int current_machine, best_machine;
    double current_score, best_score;
    double weight_cost, weight_time;
    
    if (nMachines <= 1) return;
    
    current_machine = ind->gene[job][op];
    best_machine = current_machine;
    
    /* Rango amplio de pesos para explorar todo el frente Pareto */
    weight_cost = randomperc();
    weight_time = 1.0 - weight_cost;
    
    best_score = weight_cost * ProcessingCost[job][current_machine][op] + 
                 weight_time * ProcessingTime[job][current_machine][op];
    
    for (m = 0; m < nMachines; m++)
    {
        if (m == current_machine) continue;
        
        current_score = weight_cost * ProcessingCost[job][m][op] + 
                       weight_time * ProcessingTime[job][m][op];
        
        if (current_score < best_score)
        {
            best_score = current_score;
            best_machine = m;
        }
        else if (randomperc() < 0.20)
        {
            best_machine = m;
            break;
        }
    }
    
    if (best_machine != current_machine)
    {
        ind->gene[job][op] = best_machine;
        nbinmut++;
    }
}

void scheduler_mutate_smart (individual *ind)
{
    int j, k;
    int total_genes;
    double pmut_smart;
    
    total_genes = nJobs * nOps;
    
    pmut_smart = (TARGET_FINE_MUTATIONS * 1.5) / (double)total_genes;
    
    if (pmut_smart < MIN_PMUT) pmut_smart = MIN_PMUT;
    if (pmut_smart > MAX_PMUT) pmut_smart = MAX_PMUT;
    
    if (pmut_bin > pmut_smart)
    {
        pmut_smart = pmut_bin;
    }
    
    /* Aplicar mutación inteligente gen por gen */
    for (j = 0; j < nJobs; j++)
    {
        for (k = 0; k < nOps; k++)
        {
            if (randomperc() <= pmut_smart)
            {
                mutate_single_gene_smart(ind, j, k);
            }
        }
    }
    
    /* También aplicar ocasionalmente mutación de job completo (para exploración) */
    for (j = 0; j < nJobs; j++)
    {
        if (randomperc() <= PROB_BLOCK_MUTATION * 0.5)  /* Menor prob en smart */
        {
            mutate_entire_job(ind, j);
        }
    }
    
    return;
}

/* Funciones dummy para compatibilidad si alguien llama a las viejas */
void bin_mutate_ind (individual *ind) { scheduler_mutate_hybrid(ind); }
void real_mutate_ind (individual *ind) { return; }

/* Función legacy para compatibilidad */
void scheduler_mutate_ind (individual *ind) { scheduler_mutate_hybrid(ind); }