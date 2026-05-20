/* This file contains the variable and function declarations */

# ifndef _GLOBAL_H_
# define _GLOBAL_H_

# define INF 1.0e14
# define EPS 1.0e-14
# define E  2.71828182845905
# define PI 3.14159265358979
# define GNUPLOT_COMMAND "gnuplot -persist"

typedef struct
{
    int rank;
    double constr_violation;
    double *xreal;
    int **gene; /* Usaremos esto como gene[job][operation] = machine_index */
    double *xbin;
    double *obj;
    double *constr;
    double crowd_dist;
}
individual;

typedef struct
{
    individual *ind;
}
population;

typedef struct lists
{
    int index;
    struct lists *parent;
    struct lists *child;
}
list;

/* ============================================
   ARCHIVE EXTERNO - Almacena mejores soluciones
   ============================================ */
typedef struct
{
    individual *solutions;  /* Array de individuos no dominados */
    int size;               /* Tamaño actual del archivo */
    int max_size;           /* Capacidad máxima */
}
archive;

/* --- NUEVAS ESTRUCTURAS PARA SCHEDULING --- */
/* Eliminamos struct truck, depot, client */

/* No necesitamos structs complejas, usaremos arrays globales para los parametros */
/* Las dimensiones se leeran del archivo */

extern int nJobs;      /* Cantidad de productos (P) */
extern int nMachines;  /* Cantidad de maquinas (M) */
extern int nOps;       /* Cantidad de operaciones (O) */

/* Matrices de datos [Job][Machine][Operation] */
/* Usamos punteros triples para asignar memoria dinamicamente segun el .dat */
extern double ***ProcessingTime; 
extern double ***ProcessingCost;

/* Variables estandar de NSGA-II */
extern int nreal;
extern int nbin;
extern int nobj;
extern int ncon;
extern int popsize;
extern double pcross_real;
extern double pcross_bin;
extern double pmut_real;
extern double pmut_bin;
extern double eta_c;
extern double eta_m;
extern int ngen;
extern int nbinmut;
extern int nrealmut;
extern int nbincross;
extern int nrealcross;
extern int *nbits;
extern double *min_realvar;
extern double *max_realvar;
extern double *min_binvar;
extern double *max_binvar;
extern int bitlength;
extern int choice;
extern int obj1;
extern int obj2;
extern int obj3;
extern int angle1;
extern int angle2;

/* Switches de experimentación (1=activo, 0=desactivado; default 1) */
extern int enable_diversity;     /* reinicio parcial, penalización duplicados, init mixta, búsqueda local */
extern int enable_preservation;  /* archivo externo e inyección periódica */

/* Prototipos de funciones */
void allocate_memory_pop (population *pop, int size);
void allocate_memory_ind (individual *ind);
void deallocate_memory_pop (population *pop, int size);
void deallocate_memory_ind (individual *ind);
void report_detailed_debug(population *pop, FILE *fpt);

double maximum (double a, double b);
double minimum (double a, double b);
int are_genes_equal (individual *ind1, individual *ind2);
int are_objectives_equal (individual *ind1, individual *ind2);

/* Funciones de búsqueda local */
void local_search_cost (individual *ind);
void local_search_time (individual *ind);
void local_search_balanced (individual *ind, double weight_cost, double weight_time);
void apply_local_search_to_best (population *pop, int num_to_improve);

void crossover (individual *parent1, individual *parent2, individual *child1, individual *child2);
/* Quitamos realcross y bincross del header global si no son estrictamente necesarias aqui, 
   o las adaptaremos luego. Por ahora las dejamos declaradas. */
void realcross (individual *parent1, individual *parent2, individual *child1, individual *child2);
void bincross (individual *parent1, individual *parent2, individual *child1, individual *child2);

void assign_crowding_distance_list (population *pop, list *lst, int front_size);
void assign_crowding_distance_indices (population *pop, int c1, int c2);
void assign_crowding_distance (population *pop, int *dist, int **obj_array, int front_size);

void decode_pop (population *pop);
void decode_ind (individual *ind);

void onthefly_display (population *pop, FILE *gp, int ii);

int check_dominance (individual *a, individual *b);

void evaluate_pop (population *pop);
void evaluate_ind (individual *ind);

void fill_nondominated_sort (population *mixed_pop, population *new_pop);
void crowding_fill (population *mixed_pop, population *new_pop, int count, int front_size, list *cur);
int is_duplicate_in_pop (population *new_pop, individual *ind, int current_count);

void initialize_pop (population *pop);
void initialize_pop_random (population *pop);
void initialize_ind (individual *ind);

void insert (list *node, int x);
list* del (list *node);

void merge(population *pop1, population *pop2, population *pop3);
void copy_ind (individual *ind1, individual *ind2);

void mutation_pop (population *pop);
void mutation_ind (individual *ind);
void bin_mutate_ind (individual *ind);
void real_mutate_ind (individual *ind);

void test_problem (double *xreal, double *xbin, int **gene, double *obj, double *constr);

void assign_rank_and_crowding_distance (population *new_pop);

void report_pop (population *pop, FILE *fpt);
void report_feasible (population *pop, FILE *fpt);
void report_ind (individual *ind, FILE *fpt);
void export_solutions_csv(population *pop, const char *instance_name);

void quicksort_front_obj(population *pop, int objcount, int obj_array[], int obj_array_size);
void q_sort_front_obj(population *pop, int objcount, int obj_array[], int left, int right);
void quicksort_dist(population *pop, int *dist, int front_size);
void q_sort_dist(population *pop, int *dist, int left, int right);

void selection (population *old_pop, population *new_pop);
individual* tournament (individual *ind1, individual *ind2);

/* Nuevo: Funcion de lectura general */
int readInputFile(char* filePath);

/* Funcion para liberar memoria del problema */
void freeProblemMemory(void);

/* ============================================
   ARCHIVE EXTERNO - Funciones
   ============================================ */
void allocate_archive (archive *arch, int max_size);
void deallocate_archive (archive *arch);
void update_archive (archive *arch, population *pop);
void inject_archive_to_pop (archive *arch, population *pop);
void report_archive (archive *arch, FILE *fpt);

/* ============================================
   REINICIO PARCIAL - Funciones
   ============================================ */
int count_unique_solutions (population *pop);
void check_and_partial_restart (population *pop, int generation);
void initialize_pop_mixed (population *pop);
void initialize_ind_greedy_cost (individual *ind);
void initialize_ind_greedy_time (individual *ind);
void initialize_ind_greedy_balanced (individual *ind);

# endif