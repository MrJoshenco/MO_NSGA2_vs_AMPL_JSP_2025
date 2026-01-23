/* Routine for reading SIMPLIFIED data files (.txt) */
/* Lee formato plano: nJobs nMachines nOps, seguido de Costos y Tiempos */

# include <stdio.h>
# include <stdlib.h>
# include "global.h"

int nJobs = 0;
int nMachines = 0;
int nOps = 0;

double ***ProcessingTime;
double ***ProcessingCost;

void allocateProblemMemory() {
    int i, j;
    
    ProcessingCost = (double ***)malloc(nJobs * sizeof(double **));
    ProcessingTime = (double ***)malloc(nJobs * sizeof(double **));
    
    for (i = 0; i < nJobs; i++) {
        ProcessingCost[i] = (double **)malloc(nMachines * sizeof(double *));
        ProcessingTime[i] = (double **)malloc(nMachines * sizeof(double *));
        for (j = 0; j < nMachines; j++) {
            ProcessingCost[i][j] = (double *)calloc(nOps, sizeof(double));
            ProcessingTime[i][j] = (double *)calloc(nOps, sizeof(double));
        }
    }
}

int readInputFile(char* filePath) {
    FILE* fh = fopen(filePath, "r");
    int i, j, k;
    
    if (fh == NULL) {
        printf("Error: File %s not found.\n", filePath);
        exit(1);
    }

    printf("Reading SIMPLE data file: %s ...\n", filePath);

    /* 1. Leer Dimensiones */
    if (fscanf(fh, "%d %d %d", &nJobs, &nMachines, &nOps) != 3) {
        printf("Error reading dimensions header.\n");
        exit(1);
    }
    printf("Dimensions: %d Jobs, %d Machines, %d Ops\n", nJobs, nMachines, nOps);

    allocateProblemMemory();

    /* 2. Leer Costos (Orden P -> M -> O) */
    printf("Reading Costs...\n");
    for (i = 0; i < nJobs; i++) {
        for (j = 0; j < nMachines; j++) {
            for (k = 0; k < nOps; k++) {
                if (fscanf(fh, "%lf", &ProcessingCost[i][j][k]) != 1) {
                    printf("Error reading Cost at Job %d, Machine %d, Op %d\n", i+1, j+1, k+1);
                    exit(1);
                }
            }
        }
    }

    /* 3. Leer Tiempos (Orden P -> M -> O) */
    printf("Reading Times...\n");
    for (i = 0; i < nJobs; i++) {
        for (j = 0; j < nMachines; j++) {
            for (k = 0; k < nOps; k++) {
                if (fscanf(fh, "%lf", &ProcessingTime[i][j][k]) != 1) {
                    printf("Error reading Time at Job %d, Machine %d, Op %d\n", i+1, j+1, k+1);
                    exit(1);
                }
            }
        }
    }

    fclose(fh);
    printf("Data loaded successfully.\n");
    return 1;
}

/* Function to free memory allocated for problem data */
void freeProblemMemory() {
    int i, j;
    
    if (ProcessingCost != NULL) {
        for (i = 0; i < nJobs; i++) {
            if (ProcessingCost[i] != NULL) {
                for (j = 0; j < nMachines; j++) {
                    free(ProcessingCost[i][j]);
                }
                free(ProcessingCost[i]);
            }
        }
        free(ProcessingCost);
        ProcessingCost = NULL;
    }
    
    if (ProcessingTime != NULL) {
        for (i = 0; i < nJobs; i++) {
            if (ProcessingTime[i] != NULL) {
                for (j = 0; j < nMachines; j++) {
                    free(ProcessingTime[i][j]);
                }
                free(ProcessingTime[i]);
            }
        }
        free(ProcessingTime);
        ProcessingTime = NULL;
    }
    
    printf("Problem memory freed successfully.\n");
}