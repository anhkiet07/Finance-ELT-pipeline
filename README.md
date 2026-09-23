# Finance ELT Pipeline — VN Stock & FX Data Pipeline

[![CI](https://github.com/anhkiet07/Finance-ELT-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/anhkiet07/Finance-ELT-pipeline/actions/workflows/ci.yml)

An end-to-end ELT (Extract–Load–Transform) pipeline for Vietnamese bank stock prices and USD/VND exchange rate data, built as a hands-on portfolio project for a Data Engineer role.

## Project Goal

This project is a learning-by-building exercise that simulates a realistic data platform workflow: ingest public financial data, land it in a warehouse, model it through clean layers, and surface it for BI consumption. The focus is on applying standard data engineering practices — orchestration, layered transformation, testing, and containerized local development — rather than on the financial data itself.

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
| Orchestration | Apache Airflow 2.9 | Done (daily ingest → dbt run → dbt test DAG) |
| Transformation | dbt-core (dbt-postgres, dbt_utils) | Done (staging + mart models, tests, docs) |
| Data ingestion | Python, [vnstock](https://github.com/thinh-vu/vnstock) | Working (dates still hardcoded) |
| Warehouse | PostgreSQL | Done |
| Local environment | Docker Compose | Done |
| BI / Visualization | Power BI | Connected to the mart layer |
| CI/CD | GitHub Actions | CI done (dbt run + test on push/PR, passing); no CD/deploy step |

The pipeline works end to end: the Docker Compose setup for local development (Airflow + Postgres) is in place, and an Airflow DAG runs daily to load stock prices and the USD/VND rate into the warehouse's raw tables and then build and test the dbt staging and mart models. A GitHub Actions workflow runs the dbt models and tests against a throwaway Postgres on every push and pull request, and it passes on `main`. Power BI connects to the warehouse to report on the mart layer, and dbt docs are generated for the models.

## Repository Structure

`dags/`, `dbt/`, `scripts/`, `docker/` and `.github/` contain working code; `plugins/` is still an empty placeholder.

```
finance-elt-pipeline/
├── .github/    # GitHub Actions CI workflow (dbt run + dbt test)
├── dags/       # Airflow DAGs (finance_elt_dag.py: daily ingest -> dbt run -> dbt test)
├── dbt/        # dbt project: staging and mart models, tests and CI fixtures
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

`dags/finance_elt_dag.py` defines the `finance_elt_ingest` DAG with three tasks in sequence:

- Schedule: `@daily`, `catchup=False`
- `ingest_stock_and_fx` (`PythonOperator`): creates the raw tables if needed, fetches prices for each ticker and the current USD/VND rate, and upserts them into the warehouse. It imports the functions from `scripts/ingest_stock.py`, so the logic lives in one place.
- `dbt_run` (`BashOperator`): runs `dbt run` against the `dbt/` project, building the staging and mart models on top of the freshly loaded raw data.
- `dbt_test` (`BashOperator`): runs `dbt test` to validate the models that were just built.

`ingest_stock_and_fx >> dbt_run >> dbt_test`, so the transform only runs after ingestion succeeds and the tests run on the freshly built models. New DAGs are paused by default: enable `finance_elt_ingest` in the UI and click **Trigger** to run it, or check that it parses with `docker exec airflow-scheduler airflow dags list-import-errors`.

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

The connection profile lives in `dbt/profiles/profiles.yml` and reads `WAREHOUSE_DB_*` from the environment (`WAREHOUSE_DB_HOST` and `WAREHOUSE_DB_PORT` are optional and default to `warehouse-db` / `5432`), so it works both on the host and inside the Airflow containers (where `DBT_PROFILES_DIR` is set to `/opt/airflow/dbt/profiles`). To run it from the host:

```
cd dbt
export WAREHOUSE_DB_USER=... WAREHOUSE_DB_PASSWORD=... WAREHOUSE_DB_NAME=...  # from docker/.env
export WAREHOUSE_DB_HOST=localhost WAREHOUSE_DB_PORT=5434
export DBT_PROFILES_DIR=./profiles
dbt deps
dbt run
dbt test
```

The project depends on [dbt_utils](https://github.com/dbt-labs/dbt-utils) (`dbt/packages.yml`, pinned in `package-lock.yml`). `dbt_packages/` is git-ignored and the Airflow DAG does not run `dbt deps`, so run `dbt deps` once (on the host, or with `docker exec airflow-scheduler bash -c "cd /opt/airflow/dbt && dbt deps"`) before the first DAG run; since `dbt/` is mounted into the containers, the installed packages are shared.

#### dbt tests

Tests are declared next to the models in `_staging__models.yml` and `_marts__models.yml`:

- `stg_stock_price` — `not_null` on `ticker`, `trade_date`, `close_price`; `ticker, trade_date` unique together (`dbt_utils.unique_combination_of_columns`)
- `stg_fx_rate` — `rate_date` `not_null` and `unique`; `usd_vnd_rate` `not_null`
- `mart_stock_usd` — `ticker` `not_null`; `ticker, trade_date` unique together

#### dbt docs

The model documentation and lineage graph are built with dbt docs:

```
cd dbt
dbt docs generate
dbt docs serve   # opens the docs site at http://localhost:8080 by default
```

If the Airflow UI is already running on port `8080`, use `dbt docs serve --port 8081`. The generated files go to `dbt/target/`, which is git-ignored.

### Power BI

Power BI Desktop connects to the warehouse Postgres from the host:

- Server: `localhost:5434`, database: `WAREHOUSE_DB_NAME` from `docker/.env`
- Credentials: `WAREHOUSE_DB_USER` / `WAREHOUSE_DB_PASSWORD`
- Tables: the mart models (e.g. `mart_stock_usd`) in the warehouse

The Docker stack must be running for Power BI to refresh.

### CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request to `main`:

1. Starts a `postgres:16-alpine` service container as a throwaway warehouse
2. Installs `dbt-postgres==1.11.0` (same version as the Airflow image)
3. Creates the raw tables and loads a small fixture dataset from `dbt/tests/fixtures/seed_raw_data.sql`
4. Runs `dbt deps`, `dbt run` and `dbt test`, pointing the profile at the service container via `WAREHOUSE_DB_*` variables

The CI never calls vnstock or the Vietcombank feed, so it is fast (under a minute) and deterministic. Run results are on the repository's [Actions tab](https://github.com/anhkiet07/Finance-ELT-pipeline/actions/workflows/ci.yml). There is no CD step: the pipeline runs locally in Docker, so there is nothing to deploy yet.

## Project Status

The project is complete up to CI with GitHub Actions and is no longer under active development. All planned phases are done:

**Phase 0 — Repository setup**
- [x] Initialize repository, add license
- [x] Write project README
- [x] Scaffold project structure (`dags/`, `dbt/`, `docker/`, `scripts/`, `docs/`)

**Phase 1 — Environment & ingestion**
- [x] Set up Docker Compose (Airflow + Postgres)
- [x] Build ingestion script for stock prices (vnstock) and USD/VND FX rate (Vietcombank)
- [x] Load raw data into the Postgres raw layer (`raw_stock_price`, `raw_fx_rate`, idempotent upserts)
- [x] Orchestrate ingestion with an Airflow DAG (`finance_elt_ingest`, daily)

**Phase 2 — Transformation**
- [x] Set up dbt project against the warehouse
- [x] Build staging models (typing, cleaning, deduplication)
- [x] Build mart models (price + FX joins)
- [x] Wire `dbt run` into the Airflow DAG after ingestion
- [x] Add dbt tests (`not_null`, `unique`, `dbt_utils` composite keys) and run `dbt test` in the DAG
- [x] Generate dbt docs

**Phase 3 — BI & CI/CD**
- [x] Connect Power BI to the mart layer
- [x] Add GitHub Actions CI running `dbt run` + `dbt test` against fixture data

## Future Improvements

Possible directions for extending the project:

- **Incremental ingestion** — replace the hardcoded start date with a date range or incremental loads based on the latest `trade_date` in the warehouse, and add retry/error handling around the API calls.
- **Historical FX data** — the Vietcombank feed only returns the current day's rate; a historical source would allow backfilling `raw_fx_rate` so older prices can be converted to USD.
- **Self-contained dbt dependencies** — run `dbt deps` in the Airflow Dockerfile or as a DAG task, so `dbt_utils` does not have to be installed manually.
- **Linting in CI** — add SQLFluff for the dbt models and ruff for the Python code.
- **Continuous deployment** — build and push the Airflow image and deploy the stack to a cloud VM or managed service (e.g. a cloud-hosted Postgres and Airflow) instead of running only locally.
- **Richer data** — more tickers and sectors, company fundamentals, or intraday data, with additional mart models for returns and volatility.
- **Monitoring** — Airflow failure alerts (email/Slack) and dbt source freshness checks.

## Author / Contact

**Nguyễn Anh Kiệt**
GitHub: [@anhkiet07](https://github.com/anhkiet07)
