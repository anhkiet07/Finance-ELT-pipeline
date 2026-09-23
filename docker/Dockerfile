FROM apache/airflow:2.9.3

USER root
RUN apt-get update && apt-get install -y git && apt-get clean
USER airflow

COPY scripts/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
RUN pip install --no-cache-dir dbt-postgres==1.11.0