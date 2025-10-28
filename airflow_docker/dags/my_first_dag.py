"""
My first Airflow DAG.

Why:
- Prove the environment runs a simple, reliable workflow.
How:
- Two Bash tasks: show the date, then print a friendly message.
- Scheduled daily; catchup off so we don't backfill history.
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator  # modern import in Airflow 2.x

with DAG(
    dag_id="my_first_dag",
    description="A simple tutorial DAG (date -> say hi)",
    schedule="@daily",                    # run once a day
    start_date=datetime(2023, 1, 1),      # safe, in the past
    catchup=False,                        # don't backfill old runs
    is_paused_upon_creation=False,        # show as enabled by default
) as dag:
    print_date = BashOperator(
        task_id="print_date",
        bash_command="date",              # prints current date/time
    )

    say_hi = BashOperator(
        task_id="say_hi",
        bash_command="echo 'Hello from Airflow on Python 3.12!'",  # simple, deterministic output
    )

    # Order: print_date runs before say_hi
    print_date >> say_hi