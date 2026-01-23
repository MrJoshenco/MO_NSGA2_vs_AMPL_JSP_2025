/* Routine for merge population (DEBUG VERSION) */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Variable estatica para imprimir el debug solo la primera vez */
static int copy_debug_printed = 0;

/* Routine to copy an individual 'ind1' into 'ind2' */
void copy_ind (individual *ind1, individual *ind2)
{
    int i, j;

    /* 1. Copiar Metadatos y Objetivos */
    ind2->rank = ind1->rank;
    ind2->constr_violation = ind1->constr_violation;
    ind2->crowd_dist = ind1->crowd_dist;
    
    for (i=0; i<nobj; i++)
    {
        ind2->obj[i] = ind1->obj[i];
    }
    
    if (ncon!=0)
    {
        for (i=0; i<ncon; i++)
        {
            ind2->constr[i] = ind1->constr[i];
        }
    }

    /* 2. COPIAR GENES (CRÍTICO) */
    /* Verificamos si las dimensiones son validas */
    if (nJobs > 0 && nOps > 0) 
    {
        /* DEBUG: Imprimir la primera vez que entramos aquí */
        if (copy_debug_printed == 0) {
            printf("\n[DEBUG MERGE] Copying genes detected! Jobs=%d, Ops=%d\n", nJobs, nOps);
            copy_debug_printed = 1;
        }

        for (i=0; i<nJobs; i++)
        {
            for (j=0; j<nOps; j++)
            {
                /* Copia real del valor de la maquina */
                ind2->gene[i][j] = ind1->gene[i][j];
            }
        }
    }
    else 
    {
        if (copy_debug_printed == 0) {
            printf("\n[!!! ALERTA MERGE] nJobs es 0. NO SE ESTAN COPIANDO LOS GENES.\n");
            copy_debug_printed = 1;
        }
    }

    return;
}

/* Routine to merge two populations into one */
void merge(population *pop1, population *pop2, population *pop3)
{
    int i, k;
    for (i=0; i<popsize; i++)
    {
        copy_ind (&(pop1->ind[i]), &(pop3->ind[i]));
    }
    for (i=0, k=popsize; i<popsize; i++, k++)
    {
        copy_ind (&(pop2->ind[i]), &(pop3->ind[k]));
    }
    return;
}