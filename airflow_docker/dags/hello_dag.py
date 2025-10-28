"""
Hello World DAG for Apache Airflow (Python 3.12)

Why: Sanity-check that the Dockerized Airflow stack is healthy and can
      import and execute a simple task end-to-end on your machine.
How:  Uses PythonOperator to log a friendly message; scheduled daily with
      catchup disabled so it runs only for new intervals.
"""

from __future__ import annotations

import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def _say_hello() -> None:
    """Emit a simple hello line to the task logs.

    Notes
    -----
    - Uses Python's logging so the message appears in Airflow's task logs
      and is persisted under the mapped `logs/` directory.
    """
    logging.info("Hello from Airflow on Python 3.12!")


with DAG(
    dag_id="hello_world",
    description="Minimal hello world DAG to validate the environment",
    schedule="@daily",  # Prefer the modern `schedule` over deprecated `schedule_interval`
    start_date=datetime(2023, 1, 1),
    catchup=False,
    is_paused_upon_creation=False,  # Ensure it shows as enabled by default
) as dag:
    hello_task = PythonOperator(
        task_id="hello_task",
        python_callable=_say_hello,
    )


