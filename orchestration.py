import os
import subprocess
from dagster import asset, Definitions, AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

# Chemins absolus
PROJECT_DIR = os.getcwd()
DBT_PROJECT_DIR = os.path.join(PROJECT_DIR, "dbt_pmo")
ENRICH_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "enrich_pmo.py")
DUCKDB_PATH = os.path.join(PROJECT_DIR, "data", "pmo_sentinel.duckdb")
PARQUET_PATH = os.path.join(PROJECT_DIR, "data/enriched/pmo_final.parquet")

# 1. ASSET : Enrichissement (Python)
@asset(group_name="preparation")
def pmo_enriched_csv(context: AssetExecutionContext):
    """Exécute le script Python pour transformer le CSV brut en données PMO."""
    context.log.info("Lancement de l'enrichissement Python...")
    subprocess.run(["python3", ENRICH_SCRIPT], check=True)
    return "data/enriched/pmo_enriched.csv"

# 2. ASSETS : dbt (SQL Transformation)
@dbt_assets(manifest=os.path.join(DBT_PROJECT_DIR, "target", "manifest.json"))
def dbt_pmo_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["run"], context=context).stream()

# 3. ASSET : Export Parquet (BI Bridge)
@asset(
    deps=[dbt_pmo_assets],
    group_name="distribution"
)
def pmo_final_parquet(context: AssetExecutionContext):
    """Exporte la table finale de DuckDB vers Parquet pour Power BI."""
    context.log.info("Exportation vers Parquet...")
    query = f"COPY (SELECT * FROM main.fct_pmo_portfolio) TO '{PARQUET_PATH}' (FORMAT PARQUET);"
    subprocess.run(["duckdb", DUCKDB_PATH, "-c", query], check=True)
    context.log.info(f"Fichier exporté : {PARQUET_PATH}")

# Définitions de l'instance Dagster
defs = Definitions(
    assets=[pmo_enriched_csv, dbt_pmo_assets, pmo_final_parquet],
    resources={
        "dbt": DbtCliResource(project_dir=DBT_PROJECT_DIR),
    },
)
