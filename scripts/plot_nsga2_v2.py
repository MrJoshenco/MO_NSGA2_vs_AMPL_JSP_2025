
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def clean_decimal_errors(val):
    """
    Corrige valores que perdieron el punto decimal.
    Si el valor es > 10, lo divide por 1000.
    """
    try:
        float_val = float(val)
        if float_val > 10:
            return float_val / 1000
        return float_val
    except (ValueError, TypeError):
        return val

def analyze_nsga2_results(file_path):
    # 1. Carga de datos
    df = pd.read_csv(file_path)
    
    # 2. Limpieza de datos (Hypervolume y Score)
    df['Hypervolume'] = df['Hypervolume'].apply(clean_decimal_errors)
    df['Score'] = df['Score'].apply(clean_decimal_errors)
    
    # Creamos una columna de 'Configuración' para el eje X
    # Unimos Popsize y Ngen para identificar cada setup único
    df['Config'] = df['Popsize'].astype(str) + " / " + df['Ngen'].astype(str)
    
    # Ordenar por configuración para que el gráfico sea legible
    df = df.sort_values(['Popsize', 'Ngen'])

    # Configuración estética de los gráficos
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # --- Gráfico 1: Análisis de Score ---
    sns.lineplot(data=df, x='Config', y='Score', marker='o', ax=axes[0], color='teal')
    axes[0].set_title('Evaluación del Score por Configuración (Popsize/Ngen)', fontsize=14)
    axes[0].set_ylabel('Score Resultante')
    axes[0].tick_params(axis='x', rotation=45)

    # --- Gráfico 2: Análisis de Hypervolume ---
    sns.lineplot(data=df, x='Config', y='Hypervolume', marker='s', ax=axes[1], color='coral')
    axes[1].set_title('Análisis de Hypervolume por Configuración (Popsize/Ngen)', fontsize=14)
    axes[1].set_ylabel('Hypervolume')
    axes[1].set_xlabel('Configuración (Población / Generaciones)')
    axes[1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.show()

# Ejecución
if __name__ == "__main__":
    # Cambia 'TestClaude.csv' por la ruta de tu archivo completo
    analyze_nsga2_results('instancia_gigante_mixto_popsize_ngen_20260303_195058.csv')