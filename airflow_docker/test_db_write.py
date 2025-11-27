"""
Test script to verify database write functionality works.
Run this to isolate the issue from the DAG execution context.
"""
import pandas as pd
from sqlalchemy import create_engine

# Test the exact same code as the DAG
connection_string = "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"
FILTERED_PATH = "/opt/airflow/dags/output/filtered_city_census.csv"

print("Creating engine...")
engine = create_engine(
    connection_string,
    pool_pre_ping=True,
    pool_recycle=3600,
)

print(f"Reading CSV...")
df = pd.read_csv(FILTERED_PATH)
print(f"Loaded {len(df)} rows")

try:
    print("Writing to database...")
    with engine.begin() as conn:
        df.to_sql(
            name="test_filtered_city_census",
            con=conn,
            if_exists="replace",
            index=False,
            method='multi',
        )
    print(f"✓ Successfully stored {len(df)} rows in Postgres")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()
    print("Engine disposed")

