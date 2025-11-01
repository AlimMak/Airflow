from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from sqlalchemy import create_engine
import psycopg2
import io
import requests
import pandas as pd
import os 

DATA_URL = "https://raw.githubusercontent.com/practical-bootcamp/week4-assignment1-template/main/city_census.csv"
OUTPUT_PATH = "/opt/airflow/dags/output/city_census.csv"
CLEANED_PATH = "/opt/airflow/dags/output/cleaned_city_census.csv"
FILTERED_PATH = "/opt/airflow/dags/output/filtered_city_census.csv"

def download_data():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    response = requests.get(DATA_URL)
    response.raise_for_status()

    with open(OUTPUT_PATH, 'wb') as f:
        f.write(response.content)
    
    print(f"Data downloaded and saved to {OUTPUT_PATH}")

def clean_data():
    """Load CSV, coerce numeric types, impute missing values, persist cleaned CSV.

    Why: CSV contains blanks for numeric fields; pandas may treat them as objects or floats with NaN.
    How: Coerce 'age' and 'weight' to numeric (NaN on errors), fill NaNs with column medians,
         fill missing categorical values with the mode.
    """
    df = pd.read_csv(OUTPUT_PATH)

    # Ensure numeric dtype for key numeric columns
    for col in ["age", "weight"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Impute numerics with median
    for col in ["age", "weight"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Impute categoricals with mode (most frequent)
    cat_cols = df.select_dtypes(include=["object"]).columns
    for col in cat_cols:
        mode_vals = df[col].mode(dropna=True)
        if not mode_vals.empty:
            df[col] = df[col].fillna(mode_vals.iloc[0])

    df.to_csv(CLEANED_PATH, index=False)
    print(f"Data cleaned and saved to {CLEANED_PATH}")

def filter_data():
    df = pd.read_csv(CLEANED_PATH)
    df = df[df["age"] > 18]
    df = df[df["weight"] > 160]
    df.to_csv(FILTERED_PATH, index=False)
    print(f"Data filtered and saved to {FILTERED_PATH}")


def store_to_database():
    """
    Store filtered DataFrame to Postgres table 'filtered_city_census'.

    Why:
    - Avoids pandas/SQLAlchemy version edge-cases by using psycopg2 COPY for reliability/perf.

    How:
    - Drop and recreate the table with explicit types, then bulk-load via COPY FROM STDIN.
    - Uses the Docker service hostname 'postgres'.
    """
    df = pd.read_csv(FILTERED_PATH)
    print(f"Loaded {len(df)} rows from {FILTERED_PATH}")

    # Ensure integer types for numeric columns to match table schema
    # Round first to avoid values like 208.0 causing COPY int parse errors
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce").round().astype("Int64")
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").round().astype("Int64")

    # Map DataFrame columns to SQL types
    # first,last,state are TEXT; age,weight are INTEGER
    create_sql = (
        "DROP TABLE IF EXISTS filtered_city_census;\n"
        "CREATE TABLE filtered_city_census (\n"
        "  first TEXT,\n"
        "  last TEXT,\n"
        "  age INTEGER,\n"
        "  state TEXT,\n"
        "  weight INTEGER\n"
        ");"
    )

    # Establish psycopg2 connection (matches docker-compose credentials)
    conn = psycopg2.connect(
        host="postgres",
        port=5432,
        dbname="airflow",
        user="airflow",
        password="airflow",
    )
    try:
        with conn:
            with conn.cursor() as cur:
                # Create table
                cur.execute(create_sql)

                # Prepare CSV in-memory with header matching table columns
                output = io.StringIO()
                # Ensure column order matches table definition
                ordered = df[["first", "last", "age", "state", "weight"]].copy()
                # Coerce NaN to empty strings for COPY
                ordered = ordered.where(ordered.notna(), None)
                ordered.to_csv(output, index=False, header=True)
                output.seek(0)

                # COPY from STDIN (faster and robust)
                cur.copy_expert(
                    sql="COPY filtered_city_census (first,last,age,state,weight) FROM STDIN WITH CSV HEADER",
                    file=output,
                )
        print(f"✓ Stored {len(df)} rows in Postgres table 'filtered_city_census'")
    finally:
        conn.close()


with DAG(
    dag_id = "download_dataset_dag",
    start_date = datetime(2025, 10, 27),
    schedule_interval = "@once",
    catchup = False    
):

    download_task = PythonOperator(
        task_id = "download_task",
        python_callable = download_data,
    )

    clean_task = PythonOperator(
        task_id = "clean_task",
        python_callable = clean_data,
    )

    filter_task = PythonOperator(
        task_id = "filter_task",
        python_callable = filter_data,
    )

    store_task =   PythonOperator(
        task_id = "store_task",
        python_callable = store_to_database,
    )



    download_task >> clean_task >> filter_task >> store_task