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
| Orchestration | Apache Airflow | In progress |
| Transformation | dbt-core | Planned |
| Data ingestion | Python, [vnstock](https://github.com/thinh-vu/vnstock) | Planned |
| Warehouse | PostgreSQL | In progress |
| Local environment | Docker Compose | In progress |
| BI / Visualization | Metabase or Power BI | Planned |
| CI/CD | GitHub Actions | Planned |

The repository is at an early stage: the Docker Compose setup for local development (Airflow + Postgres) has landed, but ingestion, transformation, and BI layers are not implemented yet.

## Repository Structure

The directory skeleton below is in place, but each folder is currently empty (tracked with `.gitkeep`) — implementation has not started yet.

```
finance-elt-pipeline/
├── dags/       # Airflow DAGs orchestrating extraction and dbt runs
├── dbt/        # dbt project: staging and mart models, tests, docs
├── docker/     # Dockerfiles and Docker Compose setup for local development
├── scripts/    # Standalone extraction/ingestion scripts (e.g. vnstock, FX pulls)
└── docs/       # Project documentation, design notes, diagrams
```

## Running Locally

A `docker/docker-compose.yml` brings up the local development environment:

- **airflow-db** — Postgres instance storing Airflow's metadata (port `5433`)
- **warehouse-db** — Postgres instance acting as the data warehouse (port `5434`)
- **airflow-init** — one-off service that runs `airflow db migrate` and creates the admin user
- **airflow-webserver** — Airflow UI (port `8080`)
- **airflow-scheduler** — Airflow scheduler process

Before starting, create a `docker/.env` file with the following variables:

```
AIRFLOW_DB_USER=
AIRFLOW_DB_PASSWORD=
AIRFLOW_DB_NAME=
AIRFLOW_FERNET_KEY=
AIRFLOW_ADMIN_USER=
AIRFLOW_ADMIN_PASSWORD=
AIRFLOW_ADMIN_EMAIL=
```

Then start the stack from the `docker/` directory:

```
docker compose up -d
```

The Airflow UI will be available at [http://localhost:8080](http://localhost:8080). dbt is not wired into the Compose setup yet.

## Current Status & Roadmap

**Phase 0 — Repository setup**
- [x] Initialize repository, add license
- [x] Write project README
- [x] Scaffold project structure (`dags/`, `dbt/`, `docker/`, `scripts/`, `docs/`)

**Phase 1 — Environment & ingestion**
- [x] Set up Docker Compose (Airflow + Postgres)
- [ ] Build ingestion scripts for stock prices (vnstock) and USD/VND FX rate
- [ ] Load raw responses into the Postgres raw layer
- [ ] Orchestrate ingestion with an Airflow DAG

**Phase 2 — Transformation**
- [ ] Set up dbt project against the warehouse
- [ ] Build staging models (typing, cleaning, deduplication)
- [ ] Build mart models (price + FX joins)
- [ ] Add dbt tests and generate dbt docs

**Phase 3 — BI & CI/CD**
- [ ] Connect Metabase or Power BI to the mart layer
- [ ] Add GitHub Actions for CI (linting, dbt tests)

This roadmap will be updated as each phase is completed.

## Author / Contact

**Nguyễn Anh Kiệt**
GitHub: [@anhkiet07](https://github.com/anhkiet07)
