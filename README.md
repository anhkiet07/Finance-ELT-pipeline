# Finance ELT Pipeline — VN Stock & FX Data Pipeline

An end-to-end ELT (Extract–Load–Transform) pipeline for Vietnamese bank stock prices and USD/VND exchange rate data, built as a hands-on portfolio project for a Data Engineer role.

## Project Goal

This project is a learning-by-building exercise that simulates a realistic data platform workflow: ingest public financial data, land it in a warehouse, model it through clean layers, and (eventually) surface it for BI consumption. The focus is on applying standard data engineering practices — orchestration, layered transformation, testing, and containerized local development — rather than on the financial data itself.

Target stocks: Vietnamese bank tickers **VCB, TCB, ACB, BID, LPB**, sourced via the [vnstock](https://github.com/thinh-vu/vnstock) library, plus USD/VND exchange rate data.

## Architecture

Data flows through three layers, following a standard raw → staging → mart modeling approach:

![Architecture](docs/architecture.png)

- **Raw** — stores the original API response as-is (minimal transformation), for traceability and re-processing.
- **Staging** — dbt models that clean data types, deduplicate records, and standardize column names/formats.
- **Mart** — business-facing tables joining stock prices with FX rates, shaped for BI queries.

## Tech Stack

| Layer | Tool | Status |
|---|---|---|
| Orchestration | Apache Airflow 2.9 | In progress (ingest → dbt run DAG in place) |
| Transformation | dbt-core (dbt-postgres) | In progress |
| Data ingestion | Python, [vnstock](https://github.com/thinh-vu/vnstock) | In progress |
| Warehouse | PostgreSQL | In progress |
| Local environment | Docker Compose | In progress |
| BI / Visualization | Metabase or Power BI | Planned |
| CI/CD | GitHub Actions | Planned |

The repository is still at an early stage: the Docker Compose setup for local development (Airflow + Postgres) is in place, and an Airflow DAG runs daily to load stock prices and the USD/VND rate into the warehouse's raw tables and then run the dbt staging and mart models. The BI layer is not implemented yet.

## Repository Structure

`dags/`, `dbt/`, `scripts/` and `docker/` contain working code; `plugins/` is still an empty placeholder.

```
finance-elt-pipeline/
├── dags/       # Airflow DAGs (finance_elt_dag.py: daily ingest -> dbt run)
├── dbt/        # dbt project: staging and mart models against the warehouse
├── docker/     # Docker Compose setup and custom Airflow image (Dockerfile)
├── plugins/    # Airflow plugins (empty)
├── scripts/    # Ingestion script (vnstock stock prices, VCB USD/VND rate) and requirements
└── docs/       # Project documentation, design notes, diagrams
```

## Running Locally

A `docker/docker-compose.yml` brings up the local development environment:

- **airflow-db** — Postgres instance storing Airflow's metadata (port `5433`)
- **warehouse-db** — Postgres instance acting as the data warehouse (port `5434`)
- **airflow-init** — one-off service that runs `airflow db migrate` and creates the admin user
- **airflow-webserver** — Airflow UI (port `8080`)
- **airflow-scheduler** — Airflow scheduler process

The Airflow services use a custom image built from `docker/Dockerfile` (`apache/airflow:2.9.3` plus the packages in `scripts/requirements.txt` and `dbt-postgres`). `dags/`, `plugins/`, `logs/`, `scripts/` and `dbt/` are mounted into the containers, so DAG, script and dbt model edits are picked up without rebuilding; only changes to `requirements.txt` or the Dockerfile need a rebuild.

Before starting, create a `docker/.env` file with the following variables:

```
AIRFLOW_DB_USER=
AIRFLOW_DB_PASSWORD=
AIRFLOW_DB_NAME=
AIRFLOW_FERNET_KEY=
AIRFLOW_ADMIN_USER=
AIRFLOW_ADMIN_PASSWORD=
AIRFLOW_ADMIN_EMAIL=
WAREHOUSE_DB_USER=
WAREHOUSE_DB_PASSWORD=
WAREHOUSE_DB_NAME=
```

Then start the stack from the `docker/` directory (the first run builds the custom Airflow image):

```
docker compose up -d --build
```

The Airflow UI will be available at [http://localhost:8080](http://localhost:8080); log in with `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` from `docker/.env`.

### Airflow DAG

`dags/finance_elt_dag.py` defines the `finance_elt_ingest` DAG with two tasks in sequence:

- Schedule: `@daily`, `catchup=False`
- `ingest_stock_and_fx` (`PythonOperator`): creates the raw tables if needed, fetches prices for each ticker and the current USD/VND rate, and upserts them into the warehouse. It imports the functions from `scripts/ingest_stock.py`, so the logic lives in one place.
- `dbt_run` (`BashOperator`): runs `dbt run` against the `dbt/` project, building the staging and mart models on top of the freshly loaded raw data.

`ingest_stock_and_fx >> dbt_run`, so the transform only runs after ingestion succeeds. New DAGs are paused by default: enable `finance_elt_ingest` in the UI and click **Trigger** to run it, or check that it parses with `docker exec airflow-scheduler airflow dags list-import-errors`.

### Running the ingestion script

`scripts/ingest_stock.py` can also be run standalone. It detects where it runs:

- **On the host** — reads the warehouse credentials from `docker/.env` (via a relative path, so run it from the `scripts/` directory) and connects to `localhost:5434`
- **Inside Airflow** — uses the `WAREHOUSE_DB_*` variables passed in by Compose and connects to `warehouse-db:5432` over the Docker network

```
cd scripts
pip install -r requirements.txt
python ingest_stock.py
```

It creates two raw tables if they do not exist and upserts into them, so re-running is safe:

- `raw_stock_price` — daily OHLCV for VCB, TCB, ACB, BID, LPB (unique on `ticker, trade_date`)
- `raw_fx_rate` — USD/VND sell rate from the Vietcombank exchange-rate feed (unique on `rate_date`)

The stock start date is currently hardcoded (in both the script and the DAG), and the FX feed only returns the current day's rate, so there is no historical FX backfill yet.

### dbt project

`dbt/` is a standard dbt-core project (profile name `finance_elt`) with two layers:

- **Staging** (`dbt/models/staging/`) — `stg_stock_price` and `stg_fx_rate` cast types and rename columns from the `raw_stock_price` / `raw_fx_rate` sources (declared in `_staging__sources.yml`)
- **Marts** (`dbt/models/marts/`) — `mart_stock_usd` joins staged prices with the FX rate for the same date and adds a `close_price_usd` column

The connection profile lives in `dbt/profiles/profiles.yml` and reads `WAREHOUSE_DB_*` from the environment, so it works both on the host and inside the Airflow containers (where `DBT_PROFILES_DIR` is set to `/opt/airflow/dbt/profiles`). To run it from the host:

```
cd dbt
export WAREHOUSE_DB_USER=... WAREHOUSE_DB_PASSWORD=... WAREHOUSE_DB_NAME=...  # from docker/.env
export DBT_PROFILES_DIR=./profiles
dbt run
```

There are no dbt tests or generated docs yet.

## Current Status & Roadmap

**Phase 0 — Repository setup**
- [x] Initialize repository, add license
- [x] Write project README
- [x] Scaffold project structure (`dags/`, `dbt/`, `docker/`, `scripts/`, `docs/`)

**Phase 1 — Environment & ingestion**
- [x] Set up Docker Compose (Airflow + Postgres)
- [x] Build ingestion script for stock prices (vnstock) and USD/VND FX rate (Vietcombank)
- [x] Load raw data into the Postgres raw layer (`raw_stock_price`, `raw_fx_rate`, idempotent upserts)
- [ ] Parameterize the script (date range / incremental loads instead of hardcoded dates) and add error handling
- [x] Orchestrate ingestion with an Airflow DAG (`finance_elt_ingest`, daily)

**Phase 2 — Transformation**
- [x] Set up dbt project against the warehouse
- [x] Build staging models (typing, cleaning, deduplication)
- [x] Build mart models (price + FX joins)
- [x] Wire `dbt run` into the Airflow DAG after ingestion
- [ ] Add dbt tests and generate dbt docs

**Phase 3 — BI & CI/CD**
- [ ] Connect Metabase or Power BI to the mart layer
- [ ] Add GitHub Actions for CI (linting, dbt tests)

This roadmap will be updated as each phase is completed.

## Author / Contact

**Nguyễn Anh Kiệt**
GitHub: [@anhkiet07](https://github.com/anhkiet07)
