/* Routine for evaluating population members */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Variable global para imprimir debug solo una vez */
int debug_printed = 0;

void evaluate_pop (population *pop)
{
    int i;
    for (i=0; i<popsize; i++)
    {
        evaluate_ind (&(pop->ind[i]));
    }
    /* Después de la primera población, apagamos el debug para no llenar la pantalla */
    debug_printed = 1; 
    return;
}

void evaluate_ind (individual *ind)
{
    int p, o, m;
    double total_cost = 0.0;
    double total_time = 0.0;

    ind->constr_violation = 0.0;

    /* Si es la primera vez que corremos, imprimimos el detalle del primer individuo */
    if (debug_printed == 0) {
        printf("\n--- DEBUG EVALUACION (Primer Individuo) ---\n");
    }

    for (p = 0; p < nJobs; p++) 
    {
        for (o = 0; o < nOps; o++) 
        {
            m = ind->gene[p][o];
            
            /* Suma */
            double c = ProcessingCost[p][m][o];
            double t = ProcessingTime[p][m][o];
            
            total_cost += c;
            total_time += t;

            /* Imprimir detalle solo una vez para verificar */
            if (debug_printed == 0) {
                printf("Job %d Op %d -> Maq %d | Cost: %.2f | Time: %.2f\n", p+1, o+1, m+1, c, t);
            }
        }
    }

    if (debug_printed == 0) {
        printf("--- FIN DEBUG (Total Cost: %.2f) ---\n\n", total_cost);
        debug_printed = 1; // Aseguramos no imprimir más veces dentro de este loop
    }

    ind->obj[0] = total_cost;
    ind->obj[1] = total_time;
    
    return;
}