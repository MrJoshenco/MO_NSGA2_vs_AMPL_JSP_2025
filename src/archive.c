/* Archive and Partial Restart routines for NSGA-II */
/* Maintains an external archive of best non-dominated solutions */
/* Implements partial restart to escape premature convergence */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* ============================================
   ARCHIVE EXTERNO - Implementación
   ============================================
   Mantiene las mejores soluciones no-dominadas
   encontradas durante toda la ejecución.
*/

/* Allocate memory for archive */
void allocate_archive (archive *arch, int max_size)
{
    int i;
    
    arch->max_size = max_size;
    arch->size = 0;
    arch->solutions = (individual *)malloc(max_size * sizeof(individual));
    
    for (i = 0; i < max_size; i++)
    {
        allocate_memory_ind(&(arch->solutions[i]));
    }
}

/* Deallocate archive memory */
void deallocate_archive (archive *arch)
{
    int i;
    
    for (i = 0; i < arch->max_size; i++)
    {
        deallocate_memory_ind(&(arch->solutions[i]));
    }
    free(arch->solutions);
    arch->solutions = NULL;
    arch->size = 0;
    arch->max_size = 0;
}

/* Check if individual is dominated by any in archive */
int is_dominated_by_archive (archive *arch, individual *ind)
{
    int i;
    
    for (i = 0; i < arch->size; i++)
    {
        if (check_dominance(&(arch->solutions[i]), ind) == 1)
        {
            return 1;  /* ind is dominated by archive member */
        }
    }
    return 0;
}

/* Check if individual is duplicate in archive (by objectives) */
int is_duplicate_in_archive (archive *arch, individual *ind)
{
    int i;
    
    for (i = 0; i < arch->size; i++)
    {
        if (are_objectives_equal(&(arch->solutions[i]), ind))
        {
            return 1;
        }
    }
    return 0;
}

/* Remove dominated solutions from archive */
void remove_dominated_from_archive (archive *arch, individual *new_ind)
{
    int i;
    int new_size = 0;
    
    for (i = 0; i < arch->size; i++)
    {
        /* Keep solution if NOT dominated by new_ind */
        if (check_dominance(new_ind, &(arch->solutions[i])) != 1)
        {
            if (new_size != i)
            {
                /* Move to new position */
                copy_ind(&(arch->solutions[i]), &(arch->solutions[new_size]));
            }
            new_size++;
        }
    }
    
    arch->size = new_size;
}

/* Update archive with new non-dominated solutions from population */
void update_archive (archive *arch, population *pop)
{
    int i;
    int added = 0;
    
    for (i = 0; i < popsize; i++)
    {
        /* Only consider Pareto front (rank 1) individuals */
        if (pop->ind[i].rank != 1) continue;
        
        /* Skip if dominated by archive */
        if (is_dominated_by_archive(arch, &(pop->ind[i]))) continue;
        
        /* Skip if duplicate */
        if (is_duplicate_in_archive(arch, &(pop->ind[i]))) continue;
        
        /* Remove any archive members dominated by this new solution */
        remove_dominated_from_archive(arch, &(pop->ind[i]));
        
        /* Add to archive if space available */
        if (arch->size < arch->max_size)
        {
            copy_ind(&(pop->ind[i]), &(arch->solutions[arch->size]));
            arch->size++;
            added++;
        }
        else
        {
            /* Archive is full - replace worst crowding distance solution */
            /* For simplicity, we keep existing solutions if archive is full */
            /* A more sophisticated approach would use crowding distance */
        }
    }
}

/* Inject some archive solutions back into population */
void inject_archive_to_pop (archive *arch, population *pop)
{
    int i, j;
    int num_to_inject;
    int target_idx;
    
    if (arch->size == 0) return;
    
    /* Inject up to 10% of population from archive */
    num_to_inject = popsize / 10;
    if (num_to_inject > arch->size) num_to_inject = arch->size;
    if (num_to_inject < 1) num_to_inject = 1;
    
    /* Replace worst individuals (last ones after sorting) */
    for (i = 0; i < num_to_inject; i++)
    {
        target_idx = popsize - 1 - i;  /* Replace from the end */
        
        /* Random archive solution */
        j = rnd(0, arch->size - 1);
        
        copy_ind(&(arch->solutions[j]), &(pop->ind[target_idx]));
    }
}

/* Report archive contents to file */
void report_archive (archive *arch, FILE *fpt)
{
    int i, j;
    
    fprintf(fpt, "\n===== ARCHIVE CONTENTS (%d solutions) =====\n", arch->size);
    
    for (i = 0; i < arch->size; i++)
    {
        fprintf(fpt, "Archive[%d]: ", i);
        for (j = 0; j < nobj; j++)
        {
            fprintf(fpt, "Obj%d=%.2f ", j+1, arch->solutions[i].obj[j]);
        }
        fprintf(fpt, "\n");
    }
    fprintf(fpt, "===========================================\n\n");
}

/* ============================================
   REINICIO PARCIAL - Implementación
   ============================================
   Detecta convergencia prematura y reinicia
   parte de la población para escapar de ella.
*/

/* Count unique solutions in population by objectives */
int count_unique_solutions (population *pop)
{
    int i, j;
    int unique_count = 0;
    int is_unique;
    
    for (i = 0; i < popsize; i++)
    {
        is_unique = 1;
        for (j = 0; j < i; j++)
        {
            if (are_objectives_equal(&(pop->ind[i]), &(pop->ind[j])))
            {
                is_unique = 0;
                break;
            }
        }
        if (is_unique) unique_count++;
    }
    
    return unique_count;
}

/* Check for convergence and perform partial restart if needed */
void check_and_partial_restart (population *pop, int generation)
{
    int unique_count;
    int i;
    int restart_start;
    double diversity_ratio;
    
    /* Only check every 10 generations to avoid overhead */
    if (generation % 10 != 0) return;
    
    /* Don't restart in first 20% of generations */
    if (generation < ngen / 5) return;
    
    unique_count = count_unique_solutions(pop);
    diversity_ratio = (double)unique_count / (double)popsize;
    
    /* Threshold: restart if less than 25% unique solutions */
    if (diversity_ratio < 0.25)
    {
        printf("\n [!] Gen %d: Convergencia detectada (%.1f%% unicas). Reiniciando 40%% poblacion...\n",
               generation, diversity_ratio * 100.0);
        
        /* Keep the best 60%, restart 40% */
        restart_start = (int)(popsize * 0.6);
        
        for (i = restart_start; i < popsize; i++)
        {
            double r = randomperc();
            
            /* Mayoritariamente aleatorio para maximizar diversidad en el reinicio */
            if (r < 0.10)
            {
                initialize_ind_greedy_cost(&(pop->ind[i]));
            }
            else if (r < 0.20)
            {
                initialize_ind_greedy_time(&(pop->ind[i]));
            }
            else if (r < 0.30)
            {
                initialize_ind_greedy_balanced(&(pop->ind[i]));
            }
            else
            {
                initialize_ind(&(pop->ind[i]));
            }
            
            /* Evaluate the new individual */
            evaluate_ind(&(pop->ind[i]));
        }
        
        printf(" [+] Reinicio completado. Nuevas soluciones inyectadas.\n");
    }
}
