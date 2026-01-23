/* Memory allocation and deallocation routines */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Function to allocate memory to a population */
void allocate_memory_pop (population *pop, int size)
{
    int i;
    pop->ind = (individual *)malloc(size*sizeof(individual));
    for (i=0; i<size; i++)
    {
        allocate_memory_ind (&(pop->ind[i]));
    }
    return;
}

/* Function to allocate memory to an individual */
void allocate_memory_ind (individual *ind)
{
    int j;
    
    /* SCHEDULING ADAPTATION:
       Eliminamos xreal y xbin.
       Reservamos memoria para gene como una matriz [nJobs][nOps].
       Cada celda guardará el ID de la máquina asignada.
    */
    
    ind->xreal = NULL; /* No usado */
    ind->xbin = NULL;  /* No usado */

    /* Allocation for gene [Jobs][Operations] */
    ind->gene = (int **)malloc(nJobs * sizeof(int *));
    for (j=0; j<nJobs; j++)
    {
        ind->gene[j] = (int *)malloc(nOps * sizeof(int));
    }

    /* Objectives and Constraints */
    ind->obj = (double *)malloc(nobj*sizeof(double));
    if (ncon != 0)
    {
        ind->constr = (double *)malloc(ncon*sizeof(double));
    }
    return;
}

/* Function to deallocate memory to a population */
void deallocate_memory_pop (population *pop, int size)
{
    int i;
    for (i=0; i<size; i++)
    {
        deallocate_memory_ind (&(pop->ind[i]));
    }
    free (pop->ind);
    return;
}

/* Function to deallocate memory to an individual */
void deallocate_memory_ind (individual *ind)
{
    int j;
    
    /* SCHEDULING ADAPTATION: Liberar matriz gene [nJobs] */
    for (j=0; j<nJobs; j++)
    {
        free(ind->gene[j]);
    }
    free(ind->gene);

    /* Free standard arrays */
    free(ind->obj);
    if (ncon != 0)
    {
        free(ind->constr);
    }
    return;
}