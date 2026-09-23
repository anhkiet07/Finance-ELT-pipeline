from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
from airflow.operators.bash import BashOperator

sys.path.append("/opt/airflow/scripts")

from ingest_stock import (
    create_raw_stock_table,
    create_raw_fx_table,
    fetch_stock_price,
    insert_stock_data,
    fetch_fx_rates,
    insert_fx_data,
    TICKERS,
    DB_config,
)
import psycopg2


def run_ingest():
    conn = psycopg2.connect(**DB_config)

    create_raw_stock_table(conn)
    create_raw_fx_table(conn)

    for ticker in TICKERS:
        df = fetch_stock_price(ticker, start_date="2026-09-01", end_date=datetime.today().strftime("%Y-%m-%d"))
        insert_stock_data(conn, df)

    fx_data = fetch_fx_rates()
    insert_fx_data(conn, fx_data)

    conn.close()


with DAG(
    dag_id="finance_elt_ingest",
    start_date=datetime(2026, 9, 20),
    schedule_interval="@daily",
    catchup=False,
    tags=["finance", "ingest"],
) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_stock_and_fx",
        python_callable=run_ingest,
    )

    dbt_run_task = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/dbt && dbt run",
    )

    dbt_test_task = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt && dbt test",
    )

    ingest_task >> dbt_run_task >> dbt_test_task
