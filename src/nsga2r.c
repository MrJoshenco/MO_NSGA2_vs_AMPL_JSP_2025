/* NSGA-II routine (implementation of the 'main' function) */

# define _POSIX_C_SOURCE 200809L

# include <stdio.h>
# include <stdlib.h>
# include <math.h>
# include <string.h>
# include <unistd.h>
# include <time.h>

# include "global.h"

static double timespec_elapsed_sec (const struct timespec *t0, const struct timespec *t1)
{
    return (double)(t1->tv_sec - t0->tv_sec)
         + (double)(t1->tv_nsec - t0->tv_nsec) / 1e9;
}
# include "rand.h"

/* Global variables declared in global.h are defined here */
int nreal;
int nbin;
int nobj;
int ncon;
int popsize;
double pcross_real;
double pcross_bin;
double pmut_real;
double pmut_bin;
double eta_c;
double eta_m;
int ngen;
int nbinmut;
int nrealmut;
int nbincross;
int nrealcross;
int *nbits;
double *min_realvar;
double *max_realvar;
double *min_binvar;
double *max_binvar;
int bitlength;
int choice;
int obj1;
int obj2;
int obj3;
int angle1;
int angle2;

int enable_diversity = 1;
int enable_preservation = 1;
double nsga2_exec_time_sec = 0.0;

/* Seed for random number generator */
//double seed;

int main (int argc, char **argv)
{
    int i;
    FILE *fpt1;
    FILE *fpt2;
    FILE *fpt3;
    FILE *fpt4;
    FILE *fpt5;
    FILE *fpt_debug;

    population *parent_pop;
    population *child_pop;
    population *mixed_pop;
    
    /* Archive externo para guardar las mejores soluciones */
    archive best_archive;

    /* Argumentos: ./nsga2r seed input_file popsize ngen nobj pcross pmut [enable_diversity] [enable_preservation] */
    if (argc < 8)
    {
        printf("\n Usage: ./nsga2r random_seed input_file popsize ngen nobj pcross pmut [enable_diversity] [enable_preservation]\n");
        printf("   enable_diversity:     1=on (default), 0=off (reinicio, dup. crowding, init mixta, búsqueda local)\n");
        printf("   enable_preservation:  1=on (default), 0=off (archivo externo e inyección)\n");
        printf(" Example: ./nsga2r 0.5 multijobv2S.dat 100 200 2 0.9 0.05\n");
        printf(" Example: ./nsga2r 0.5 instancia_basica.txt 100 200 2 0.9 0.05 0 1\n");
        exit(1);
    }

    seed = (double)atof(argv[1]);
    if (seed<=0.0 || seed>=1.0){
        printf("\n Entered seed value is wrong, seed value must be in (0,1) \n");
        exit(1);
    }

    /* Abrir archivos de salida */
    fpt1 = fopen("initial_pop.out","w");
    fpt2 = fopen("final_pop.out","w");
    fpt3 = fopen("best_pop.out","w");
    fpt4 = fopen("all_pop.out","w");
    fpt5 = fopen("params.out","w");
    fpt_debug = fopen("solution_debug.out", "w"); // Abrir archivo

    fprintf(fpt1,"# This file contains the data of initial population\n");
    fprintf(fpt2,"# This file contains the data of final population\n");
    fprintf(fpt3,"# This file contains the data of final feasible population (if found)\n");
    fprintf(fpt4,"# This file contains the data of all generations\n");
    fprintf(fpt5,"# This file contains information about inputs as read by the program\n");

    /* 1. Leer archivo de datos AMPL */
    char * instance_route = argv[2];
    readInputFile(instance_route); /* Ahora usa el nuevo reader */

    /* 2. Configurar parametros del algoritmo */
    popsize = atoi(argv[3]);
    if (popsize<4 || (popsize%4)!= 0){
        printf("\n population size read is : %d",popsize);
        printf("\n Wrong population size entered, hence exiting \n");
        exit (1);
    }
    
    ngen = atoi(argv[4]);
    if (ngen<1){
        printf("\n number of generations read is : %d",ngen);
        exit (1);
    }
    
    nobj = atoi(argv[5]);
    if (nobj<1){
        printf("\n number of objectives entered is : %d",nobj);
        exit (1);
    }

    /* Parametros de probabilidad */
    pcross_bin = atof (argv[6]); /* Reutilizamos variable para probabilidad de cruce general */
    pmut_bin = atof (argv[7]);   /* Reutilizamos variable para probabilidad de mutacion general */

    enable_diversity = (argc >= 9) ? (atoi(argv[8]) != 0) : 1;
    enable_preservation = (argc >= 10) ? (atoi(argv[9]) != 0) : 1;
    
    /* Configuración interna para NSGA-II */
    nreal = 0; /* No usamos reales */
    nbin = 0;  /* No usamos binarios estandar */
    ncon = 0;  /* Sin restricciones explicitas por ahora */
    
    /* Imprimir parametros */
    printf("\n Input data successfully entered, now performing initialization \n");
    fprintf(fpt5,"\n Population size = %d",popsize);
    fprintf(fpt5,"\n Number of generations = %d",ngen);
    fprintf(fpt5,"\n Number of objective functions = %d",nobj);
    fprintf(fpt5,"\n Probability of crossover = %e",pcross_bin);
    fprintf(fpt5,"\n Probability of mutation = %e",pmut_bin);
    fprintf(fpt5,"\n Seed = %e",seed);
    fprintf(fpt5,"\n enable_diversity = %d", enable_diversity);
    fprintf(fpt5,"\n enable_preservation = %d", enable_preservation);
    printf("\n enable_diversity = %d, enable_preservation = %d\n",
           enable_diversity, enable_preservation);
    
    /* Inicializar contadores */
    nbincross = 0;
    nbinmut = 0;

    /* 3. Asignar Memoria */
    parent_pop = (population *)malloc(sizeof(population));
    child_pop = (population *)malloc(sizeof(population));
    mixed_pop = (population *)malloc(sizeof(population));
    
    allocate_memory_pop (parent_pop, popsize);
    allocate_memory_pop (child_pop, popsize);
    allocate_memory_pop (mixed_pop, 2*popsize);
    
    /* Asignar memoria para archive externo (solo si preservación activa) */
    if (enable_preservation)
    {
        allocate_archive (&best_archive, 2 * popsize);
    }

    /* 4. Inicialización (cronómetro: hasta fin de generaciones) */
    {
    struct timespec run_start, run_end;

    clock_gettime(CLOCK_MONOTONIC, &run_start);

    randomize(); /* Inicializar generador random con la semilla */
    if (enable_diversity)
    {
        initialize_pop_mixed (parent_pop);
    }
    else
    {
        initialize_pop_random (parent_pop);
    }
    
    printf("\n Initialization done, now performing first generation\n");
    /* decode_pop ya no es necesario, trabajamos directo con enteros */
    
    evaluate_pop (parent_pop);
    assign_rank_and_crowding_distance (parent_pop);

    report_pop (parent_pop, fpt1);
    fprintf(fpt4,"# gen = 1\n");
    report_pop(parent_pop,fpt4);
    
    printf("\n gen = 1");
    fflush(stdout);

    /* 5. Bucle Principal (Generaciones) */
    /* Búsqueda local: solo ocasionalmente y a pocas soluciones para no sesgar */
    int local_search_interval = 50;
    int local_search_count = popsize / 20;
    if (local_search_count < 2) local_search_count = 2;
    if (local_search_count > 10) local_search_count = 10;
    
    for (i=2; i<=ngen; i++)
    {
        selection (parent_pop, child_pop);
        mutation_pop (child_pop);
        evaluate_pop(child_pop);
        merge (parent_pop, child_pop, mixed_pop);
        fill_nondominated_sort (mixed_pop, parent_pop);
        
        if (enable_preservation)
        {
            update_archive(&best_archive, parent_pop);
        }
        
        if (enable_diversity)
        {
            check_and_partial_restart(parent_pop, i);
        }
        
        if (enable_diversity && i % local_search_interval == 0)
        {
            apply_local_search_to_best(parent_pop, local_search_count);
            evaluate_pop(parent_pop);
            assign_rank_and_crowding_distance(parent_pop);
        }
        
        if (enable_preservation && i % 25 == 0 && best_archive.size > 0)
        {
            inject_archive_to_pop(&best_archive, parent_pop);
        }
        
        /* Reportar */
        fprintf(fpt4,"# gen = %d\n",i);
        report_pop(parent_pop,fpt4);
        printf("\n gen = %d",i);
    }

    clock_gettime(CLOCK_MONOTONIC, &run_end);
    nsga2_exec_time_sec = timespec_elapsed_sec(&run_start, &run_end);
    fprintf(fpt5, "\n nsga2_exec_time_sec = %.3f", nsga2_exec_time_sec);
    printf("\n Tiempo de ejecucion NSGA-II: %.3f s", nsga2_exec_time_sec);
    }
    
    if (enable_preservation)
    {
        update_archive(&best_archive, parent_pop);
    }
    
    printf("\n Generations finished, now reporting solutions");
    report_pop(parent_pop,fpt2);
    report_feasible(parent_pop,fpt3);
    
    if (enable_preservation)
    {
        printf("\n Archive externo contiene %d soluciones no-dominadas", best_archive.size);
        report_archive(&best_archive, fpt_debug);
    }
    
    printf("\n Generando reporte de auditoria detallado en 'solution_debug.out'...");
    report_detailed_debug(parent_pop, fpt_debug);
    
    /* Extraer nombre base de la instancia para los archivos de exportación */
    char instance_name[256];
    char *base = strrchr(instance_route, '/');
    if (base) base++; else base = instance_route;
    strncpy(instance_name, base, sizeof(instance_name) - 1);
    instance_name[sizeof(instance_name) - 1] = '\0';
    /* Remover extensión .txt o .dat */
    char *dot = strrchr(instance_name, '.');
    if (dot) *dot = '\0';
    
    printf("\n Exportando soluciones detalladas...");
    export_solutions_csv(parent_pop, instance_name);

    /* Liberar memoria y cerrar archivos */
    fflush(stdout);
    fclose(fpt1);
    fclose(fpt2);
    fclose(fpt3);
    fclose(fpt4);
    fclose(fpt5);
    fclose(fpt_debug);

    deallocate_memory_pop (parent_pop, popsize);
    deallocate_memory_pop (child_pop, popsize);
    deallocate_memory_pop (mixed_pop, 2*popsize);
    
    if (enable_preservation)
    {
        deallocate_archive(&best_archive);
    }
    
    free (parent_pop);
    free (child_pop);
    free (mixed_pop);
    
    /* Liberar memoria global del problema */
    freeProblemMemory();

    printf("\n Routine successfully exited \n");
    return (0);
}