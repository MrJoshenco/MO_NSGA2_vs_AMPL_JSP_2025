/* Routines for storing population data into files */

# include <stdio.h>
# include <stdlib.h>
# include <math.h>

# include "global.h"
# include "rand.h"

/* Function to print the information of a population in a file */
void report_pop (population *pop, FILE *fpt)
{
    int i, j, k;
    for (i=0; i<popsize; i++)
    {
        /* 1. Imprimir Objetivos */
        for (j=0; j<nobj; j++)
        {
            fprintf(fpt,"%e\t",pop->ind[i].obj[j]);
        }

        /* 2. Imprimir Restricciones (si existen) */
        if (ncon!=0)
        {
            for (j=0; j<ncon; j++)
            {
                fprintf(fpt,"%e\t",pop->ind[i].constr[j]);
            }
        }

        /* 3. Imprimir Cromosoma (Asignación de Máquinas) */
        /* Formato: Job1_Op1 Job1_Op2 ... JobN_OpM */
        fprintf(fpt, "\t|Genes: ");
        for (j=0; j<nJobs; j++)
        {
            for (k=0; k<nOps; k++)
            {
                fprintf(fpt,"%d ", pop->ind[i].gene[j][k]);
            }
            fprintf(fpt, "| "); /* Separador visual entre trabajos */
        }

        /* 4. Imprimir Metadatos del algoritmo */
        fprintf(fpt,"%e\t",pop->ind[i].constr_violation);
        fprintf(fpt,"%d\t",pop->ind[i].rank);
        fprintf(fpt,"%e\n",pop->ind[i].crowd_dist);
    }
    return;
}

/* Function to print the information of feasible and non-dominated population in a file */
void report_feasible (population *pop, FILE *fpt)
{
    int i, j, k;
    for (i=0; i<popsize; i++)
    {
        /* Solo imprimir si es factible (violation == 0) y Rango 1 (Frente Pareto) */
        if (pop->ind[i].constr_violation == 0.0 && pop->ind[i].rank==1)
        {
            for (j=0; j<nobj; j++)
            {
                fprintf(fpt,"%e\t",pop->ind[i].obj[j]);
            }
            if (ncon!=0)
            {
                for (j=0; j<ncon; j++)
                {
                    fprintf(fpt,"%e\t",pop->ind[i].constr[j]);
                }
            }
            
            /* Imprimir Genes */
            for (j=0; j<nJobs; j++)
            {
                for (k=0; k<nOps; k++)
                {
                    fprintf(fpt,"%d ", pop->ind[i].gene[j][k]);
                }
            }

            fprintf(fpt,"%e\t",pop->ind[i].constr_violation);
            fprintf(fpt,"%d\t",pop->ind[i].rank);
            fprintf(fpt,"%e\n",pop->ind[i].crowd_dist);
        }
    }
    return;
}

/* Función para auditoría detallada de la solución */
void report_detailed_debug(population *pop, FILE *fpt)
{
    int i, j, k, m;
    double calc_cost, calc_time;
    int solution_counter = 1;

    fprintf(fpt, "\n=======================================================\n");
    fprintf(fpt, "REPORTE DETALLADO DE SOLUCIONES OPTIMAS (PARETO RANK 1)\n");
    fprintf(fpt, "=======================================================\n");

    for (i = 0; i < popsize; i++)
    {
        /* Solo auditamos las mejores soluciones (Rank 1) */
        if (pop->ind[i].rank == 1)
        {
            fprintf(fpt, "\n---> Solucion Optima #%d\n", solution_counter++);
            fprintf(fpt, "     Objetivos Reportados por NSGA-II: Costo = %.2f, Tiempo = %.2f\n", 
                    pop->ind[i].obj[0], pop->ind[i].obj[1]);
            
            fprintf(fpt, "     -------------------------------------------------------\n");
            fprintf(fpt, "     | Job | Op  | Maquina Asignada |  Costo  |  Tiempo  |\n");
            fprintf(fpt, "     -------------------------------------------------------\n");

            calc_cost = 0.0;
            calc_time = 0.0;

            /* Recalculamos manualmente para verificar */
            for (j = 0; j < nJobs; j++)
            {
                for (k = 0; k < nOps; k++)
                {
                    m = pop->ind[i].gene[j][k]; // Máquina elegida
                    
                    /* Obtenemos valores directos de la matriz */
                    double c = ProcessingCost[j][m][k];
                    double t = ProcessingTime[j][m][k];
                    
                    calc_cost += c;
                    calc_time += t;

                    fprintf(fpt, "     | %3d | %3d |      M%d        | %7.2f | %7.2f  |\n", 
                            j+1, k+1, m+1, c, t);
                }
                fprintf(fpt, "     - - - - - - - - - - - - - - - - - - - - - - - - - -\n");
            }
            
            fprintf(fpt, "     -------------------------------------------------------\n");
            fprintf(fpt, "     SUMA MANUAL AUDITADA:             Costo = %.2f, Tiempo = %.2f\n", calc_cost, calc_time);
            
            /* Verificación de integridad */
            if (fabs(calc_cost - pop->ind[i].obj[0]) > 1e-5 || fabs(calc_time - pop->ind[i].obj[1]) > 1e-5) {
                fprintf(fpt, "     [!!!] ALERTA: HAY UNA DISCREPANCIA EN LOS CALCULOS\n");
            } else {
                fprintf(fpt, "     [OK] Los calculos coinciden perfectamente.\n");
            }
        }
    }
    return;
}

/* Exportar soluciones a archivo CSV detallado */
void export_solutions_csv(population *pop, const char *instance_name)
{
    int i, j, k, m;
    double calc_cost, calc_time;
    int solution_counter = 0;
    char filename[256];
    FILE *fpt_summary, *fpt_details, *fpt_matrix;
    
    /* Contar soluciones Pareto */
    for (i = 0; i < popsize; i++) {
        if (pop->ind[i].rank == 1) solution_counter++;
    }
    
    /* 1. Archivo resumen del frente de Pareto */
    sprintf(filename, "solutions_%s_pareto.csv", instance_name);
    fpt_summary = fopen(filename, "w");
    fprintf(fpt_summary, "# FRENTE DE PARETO - %d soluciones optimas\n", solution_counter);
    fprintf(fpt_summary, "# Instancia: %s\n", instance_name);
    fprintf(fpt_summary, "# Dimensiones: %d Jobs, %d Maquinas, %d Operaciones\n", nJobs, nMachines, nOps);
    fprintf(fpt_summary, "solucion,costo_total,tiempo_total,crowding_distance\n");
    
    solution_counter = 0;
    for (i = 0; i < popsize; i++) {
        if (pop->ind[i].rank == 1) {
            solution_counter++;
            fprintf(fpt_summary, "%d,%.2f,%.2f,%.6f\n", 
                    solution_counter, 
                    pop->ind[i].obj[0], 
                    pop->ind[i].obj[1],
                    pop->ind[i].crowd_dist);
        }
    }
    fclose(fpt_summary);
    printf("\n   Exportado: %s", filename);
    
    /* 2. Archivo con detalle de asignaciones */
    sprintf(filename, "solutions_%s_details.csv", instance_name);
    fpt_details = fopen(filename, "w");
    fprintf(fpt_details, "solucion,job,operacion,maquina_asignada,costo,tiempo\n");
    
    solution_counter = 0;
    for (i = 0; i < popsize; i++) {
        if (pop->ind[i].rank == 1) {
            solution_counter++;
            for (j = 0; j < nJobs; j++) {
                for (k = 0; k < nOps; k++) {
                    m = pop->ind[i].gene[j][k];
                    fprintf(fpt_details, "%d,%d,%d,%d,%.2f,%.2f\n",
                            solution_counter,
                            j + 1,  /* Job (1-indexed) */
                            k + 1,  /* Operación (1-indexed) */
                            m + 1,  /* Máquina (1-indexed) */
                            ProcessingCost[j][m][k],
                            ProcessingTime[j][m][k]);
                }
            }
        }
    }
    fclose(fpt_details);
    printf("\n   Exportado: %s", filename);
    
    /* 3. Archivo con matriz de asignación (formato legible) */
    sprintf(filename, "solutions_%s_matrix.txt", instance_name);
    fpt_matrix = fopen(filename, "w");
    
    fprintf(fpt_matrix, "================================================================================\n");
    fprintf(fpt_matrix, "                    REPORTE DE SOLUCIONES OPTIMAS\n");
    fprintf(fpt_matrix, "================================================================================\n");
    fprintf(fpt_matrix, "Instancia: %s\n", instance_name);
    fprintf(fpt_matrix, "Dimensiones: %d Jobs x %d Maquinas x %d Operaciones\n", nJobs, nMachines, nOps);
    fprintf(fpt_matrix, "================================================================================\n\n");
    
    solution_counter = 0;
    for (i = 0; i < popsize; i++) {
        if (pop->ind[i].rank == 1) {
            solution_counter++;
            calc_cost = 0.0;
            calc_time = 0.0;
            
            fprintf(fpt_matrix, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
            fprintf(fpt_matrix, "  SOLUCION #%d\n", solution_counter);
            fprintf(fpt_matrix, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
            fprintf(fpt_matrix, "  Costo Total: %.2f\n", pop->ind[i].obj[0]);
            fprintf(fpt_matrix, "  Tiempo Total: %.2f\n", pop->ind[i].obj[1]);
            fprintf(fpt_matrix, "  Crowding Distance: %.6f\n\n", pop->ind[i].crowd_dist);
            
            /* Matriz de asignación */
            fprintf(fpt_matrix, "  MATRIZ DE ASIGNACION (Maquina asignada a cada Job/Operacion):\n");
            fprintf(fpt_matrix, "  ┌──────┬");
            for (k = 0; k < nOps; k++) fprintf(fpt_matrix, "─────┬");
            fprintf(fpt_matrix, "\b┐\n");
            
            fprintf(fpt_matrix, "  │ Job  │");
            for (k = 0; k < nOps; k++) fprintf(fpt_matrix, " Op%2d│", k + 1);
            fprintf(fpt_matrix, "\n");
            
            fprintf(fpt_matrix, "  ├──────┼");
            for (k = 0; k < nOps; k++) fprintf(fpt_matrix, "─────┼");
            fprintf(fpt_matrix, "\b┤\n");
            
            for (j = 0; j < nJobs; j++) {
                fprintf(fpt_matrix, "  │ J%3d │", j + 1);
                for (k = 0; k < nOps; k++) {
                    m = pop->ind[i].gene[j][k];
                    fprintf(fpt_matrix, " M%2d │", m + 1);
                }
                fprintf(fpt_matrix, "\n");
            }
            
            fprintf(fpt_matrix, "  └──────┴");
            for (k = 0; k < nOps; k++) fprintf(fpt_matrix, "─────┴");
            fprintf(fpt_matrix, "\b┘\n\n");
            
            /* Desglose de costos y tiempos por Job */
            fprintf(fpt_matrix, "  DESGLOSE POR JOB:\n");
            fprintf(fpt_matrix, "  ┌──────┬────────────┬─────────────┐\n");
            fprintf(fpt_matrix, "  │ Job  │   Costo    │   Tiempo    │\n");
            fprintf(fpt_matrix, "  ├──────┼────────────┼─────────────┤\n");
            
            for (j = 0; j < nJobs; j++) {
                double job_cost = 0.0, job_time = 0.0;
                for (k = 0; k < nOps; k++) {
                    m = pop->ind[i].gene[j][k];
                    job_cost += ProcessingCost[j][m][k];
                    job_time += ProcessingTime[j][m][k];
                }
                calc_cost += job_cost;
                calc_time += job_time;
                fprintf(fpt_matrix, "  │ J%3d │ %10.2f │ %11.2f │\n", j + 1, job_cost, job_time);
            }
            
            fprintf(fpt_matrix, "  ├──────┼────────────┼─────────────┤\n");
            fprintf(fpt_matrix, "  │TOTAL │ %10.2f │ %11.2f │\n", calc_cost, calc_time);
            fprintf(fpt_matrix, "  └──────┴────────────┴─────────────┘\n\n");
        }
    }
    
    fprintf(fpt_matrix, "================================================================================\n");
    fprintf(fpt_matrix, "                         FIN DEL REPORTE\n");
    fprintf(fpt_matrix, "================================================================================\n");
    
    fclose(fpt_matrix);
    printf("\n   Exportado: %s", filename);
}