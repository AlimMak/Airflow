from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
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

    download_task >> clean_task >> filter_task