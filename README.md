# Environment Data Project

A Python ETL application that retrieves environmental observations from the
Danish Meteorological Institute (DMI), transforms supported measurements, and
stores them in PostgreSQL.

The project is organized into extraction, transformation, and persistence
components, with versioned database migrations and automated unit and
integration tests.

---

## Contents

- [Features](#features)
- [Technology stack](#technology-stack)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [File overview](#file-overview)
- [Architecture](#architecture)
- [Learning objectives](#learning-objectives)
- [Author](#author)

---

## Features

- Retrieve environmental observations from the DMI API
- Transform supported temperature, humidity, CO2, and PM2.5 observations
- Store source metadata and measurements in PostgreSQL
- Apply versioned SQL migrations automatically at startup
- Run unit and integration tests with Pytest
- Use Docker Compose for local development and execution
- Manage the database through pgAdmin

---

## Technology stack

- **Python 3**
- **PostgreSQL**
- **Docker & Docker Compose**
- **Psycopg**
- **Requests**
- **Pytest**
- **pgAdmin**

---

## Getting started

### Prerequisites

- Git
- Docker Desktop with Docker Compose

### Clone the repository

```bash
git clone https://github.com/mielouise/environment_data_project.git
cd environment_data_project
```

### Start the application

```bash
docker compose up --build app
```

This builds and starts the application together with its PostgreSQL
dependency. The application initializes the database schema and runs the ETL
workflow: it requests observations from the DMI API, transforms them, and
saves the source and measurements to PostgreSQL.

To start PostgreSQL and pgAdmin for database inspection:

```bash
docker compose up -d db pgadmin
```

Open pgAdmin at:

```text
http://localhost:8080
```

Sign in with the pgAdmin credentials configured in `.env`.

When finished, stop and remove the containers with:

```bash
docker compose down
```

The PostgreSQL data volume is retained when the containers are stopped this
way.

### Testing

Run the complete test suite, including the unit tests and integration tests:

```bash
docker compose run --build --rm tests
```

The test service waits for PostgreSQL to become healthy. Integration tests
connect to the configured PostgreSQL database and make a real request to the
DMI API, so the corresponding environment variables must be configured and
the environment must have network access to DMI.

---

## Project structure

```text
environment_data_project/
├── .devcontainer/
│   ├── Dockerfile
│   ├── devcontainer-lock.json
│   └── devcontainer.json
├── app/
│   ├── __init__.py
│   ├── constants/
│   │   ├── __init__.py
│   │   └── parameters.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── dmi.py
│   ├── database.py
│   ├── migrations/
│   │   └── 0001_initial_schema.sql
│   ├── etl_service.py
│   ├── load.py
│   ├── main.py
│   └── transform.py
├── pgadmin/
│   └── servers.json
├── tests/
│   ├── __init__.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_dmi_api.py
│   │   └── test_postgres.py
│   └── unit/
│       ├── __init__.py
│       ├── test_database.py
│       ├── test_etl_service.py
│       ├── test_extract.py
│       ├── test_load.py
│       ├── test_main.py
│       └── test_transform.py
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements-dev.txt
├── requirements.txt
└── README.md
```

## File overview

- The `app` directory contains the application code. Docker starts the
  application through `app/main.py`, which orchestrates the ETL process. This
  file is therefore the recommended application entry point.
- The `app/extract` directory contains the code for retrieving data from the
  DMI API, including a shared abstraction for data sources.
- The `app/constants` directory contains shared constants, including IDs for
  the supported measurement parameters.
- The `app/migrations` directory contains versioned SQL scripts for creating
  and updating the database schema.
- `app/transform.py`, `app/load.py`, `app/database.py`, and
  `app/etl_service.py` handle data transformation, data storage, database
  connections, and orchestration of the ETL process, respectively.
- The `tests` directory contains the test suite, which is run by the `tests`
  service in Docker Compose. It is divided into two subdirectories:
  - The `tests/unit` directory contains unit tests that test application code
    in isolation from external systems, for example by using mocks.
  - The `tests/integration` directory contains integration tests that verify
    connections to external systems. `test_postgres.py` tests the connection
    to PostgreSQL, and `test_dmi_api.py` sends a request to the configured DMI
    API.
- `Dockerfile` defines the Docker image for the application and tests.
  `docker-compose.yml` configures the app, test, PostgreSQL, and pgAdmin
  services.
- `.gitignore` specifies which files Git should ignore, such as local
  environment settings. `.dockerignore` specifies which files to exclude from
  the Docker build context.
- `requirements.txt` lists the Python packages required by the application.
  `requirements-dev.txt` includes these packages along with additional
  packages needed for development and testing.
- The `.devcontainer` directory contains the development container
  configuration, and the `pgadmin` directory contains the pgAdmin
  configuration.
- `README.md` contains the project description, setup instructions, and
  database schema documentation.

---

## Architecture

The diagrams below describe the solution from four different
perspectives:

1. Application component architecture
2. UML class design
3. Runtime ETL workflow
4. Database design

Together these views document the system at component, implementation,
execution, and database levels.

### Application component overview

- Shows the main application components and their responsibilities.
- Shows how the application communicates with the DMI API and PostgreSQL.

```mermaid
flowchart LR
    subgraph Application["Application"]
        direction TB
        Main["«component»<br/>Application entry point<br/>app/main.py"]
        ETL["«component»<br/>ETL orchestrator<br/>ETLService"]
        Source["«component»<br/>DMI data source<br/>DMIDataSource"]
        Transformer["«component»<br/>Data transformer<br/>DMIDataTransformer"]
        Repository["«component»<br/>Measurement repository<br/>MeasurementRepository"]
        Database["«component»<br/>Database utilities<br/>app/database.py"]
    end

    DMI["«external system»<br/>DMI Observation API"]
    PostgreSQL[("«database»<br/>PostgreSQL")]

    Main -.->|creates and runs| ETL
    ETL -.->|uses| Source
    ETL -.->|uses| Transformer
    ETL -.->|uses| Repository
    Source <-->|HTTP observations| DMI
    Main -.->|applies migrations and opens connection| Database
    Database -->|schema and connection| PostgreSQL
    Repository -->|SQL operations| PostgreSQL

    classDef application fill:#eff6ff,stroke:#2563eb,color:#0f172a,stroke-width:1.5px
    classDef external fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-width:1.5px
    classDef datastore fill:#ecfdf5,stroke:#059669,color:#064e3b,stroke-width:1.5px

    class Main,ETL,Source,Transformer,Repository,Database application
    class DMI external
    class PostgreSQL datastore
```

### UML class diagram

- Shows the static structure of the main ETL classes, including their key
  attributes and methods.
- The solid inheritance arrow shows that `DMIDataSource` extends
  `SensorDataSource`.
- The solid associations show which data source, transformer, and repository
  `ETLService` uses.
- The dashed dependencies show that the transformer creates `MeasurementDTO`
  objects and uses `ParameterIds`, while the repository persists the DTOs.

```mermaid
classDiagram
    direction LR

    class SensorDataSource {
        <<abstract>>
        +source_id: str
        +source_name: str
        +fetch() dict
    }

    class DMIDataSource {
        +url: str
        +fetch() dict
    }

    class ETLService {
        -source: SensorDataSource
        -transformer: DMIDataTransformer
        -repository: MeasurementRepository
        +run() int
    }

    class DMIDataTransformer {
        -source_id: str
        +transform(raw_json) list~MeasurementDTO~
    }

    class MeasurementDTO {
        +source_id: str
        +parameter_id: int
        +timestamp: datetime
        +value: float
    }

    class MeasurementRepository {
        -_conn
        +save_source(source_id, source_name, source_type) None
        +save_measurements(records) None
        +close() None
    }

    class ParameterIds {
        <<enumeration>>
        TEMPERATURE
        HUMIDITY
        HUMIDITY_PAST_1H
        CO2
        PM25
    }

    SensorDataSource <|-- DMIDataSource

    ETLService --> SensorDataSource : uses
    ETLService --> DMIDataTransformer : uses
    ETLService --> MeasurementRepository : uses
    DMIDataTransformer ..> MeasurementDTO : creates
    DMIDataTransformer ..> ParameterIds : maps parameter IDs
    MeasurementRepository ..> MeasurementDTO : persists
```

### ETL workflow

The single activity diagram below shows the complete application run, including
database migrations before the ETL path, decision points, error handling, and
connection cleanup.

```mermaid
flowchart TD
    Start((Start))
    InitSchema["1. Apply pending database migrations"]
    ReadURL["2. Read DMI_API_URL"]
    HasURL{"API URL configured?"}
    BuildServices["3. Create data source, transformer,<br/>database connection, repository,<br/>and ETL service"]
    Fetch["4. Fetch observations from DMI API"]
    Transform["5. Transform supported observations<br/>into MeasurementDTO records"]
    SaveSource["6. Save DMI source metadata"]
    SaveMeasurements["7. Call save_measurements(records)"]
    HasRecords{"Any measurements?"}
    WriteRecords["Insert or update measurements<br/>in PostgreSQL"]
    NoRecords["No measurement rows to write"]
    Count["Return processed measurement count"]
    ReportSuccess["Report successful completion"]
    ReportFailure["Log error and exit<br/>with failure status"]
    Cleanup["Close application database connection<br/>if one was opened"]
    End((End))

    Start --> InitSchema --> ReadURL --> HasURL
    HasURL -->|Yes| BuildServices --> Fetch
    Transform --> SaveSource
    Fetch --> Transform
    SaveSource --> SaveMeasurements --> HasRecords
    HasRecords -->|Yes| WriteRecords --> Count
    HasRecords -->|No| NoRecords --> Count
    Count --> ReportSuccess --> Cleanup --> End
    HasURL -->|No| ReportFailure
    ReportFailure --> Cleanup

    InitSchema -. error .-> ReportFailure
    BuildServices -. error .-> ReportFailure
    Fetch -. error .-> ReportFailure
    Transform -. error .-> ReportFailure
    SaveSource -. error .-> ReportFailure
    SaveMeasurements -. error .-> ReportFailure
    WriteRecords -. error .-> ReportFailure

    classDef terminal fill:#0f766e,color:#ffffff,stroke:#115e59,stroke-width:2px
    classDef action fill:#eff6ff,color:#0f172a,stroke:#2563eb,stroke-width:1.5px
    classDef decision fill:#fff7ed,color:#0f172a,stroke:#ea580c,stroke-width:1.5px
    classDef success fill:#dcfce7,color:#14532d,stroke:#16a34a,stroke-width:1.5px
    classDef failure fill:#fee2e2,color:#7f1d1d,stroke:#dc2626,stroke-width:1.5px

    class Start,End terminal
    class InitSchema,ReadURL,BuildServices,Fetch,Transform,SaveSource,SaveMeasurements,WriteRecords,NoRecords,Count,Cleanup action
    class HasURL,HasRecords decision
    class ReportSuccess success
    class ReportFailure failure
```

The workflow proceeds as follows:

1. Apply pending database migrations to create or update the database schema.
2. Read the `DMI_API_URL` setting.
3. If the URL is configured, create the data source, transformer, database
   connection, repository, and ETL service.
4. Fetch observations from the DMI API and transform supported observations
   into measurement records.
5. Save the DMI source metadata, then insert or update the measurement records
   in PostgreSQL when any are available.
6. Report the number of processed measurements and close the database
   connection.
7. If setup or processing fails, report the error and close the database
   connection if one was opened.

#### Database migrations

The application applies pending SQL migrations automatically before starting
the ETL workflow. Migration scripts live in `app/migrations/` and are named
with a unique, increasing version and a descriptive name, for example
`0001_initial_schema.sql`. Applied versions and SHA-256 checksums are stored
in the PostgreSQL `schema_migrations` table. Migrations run in a transaction,
and a database advisory lock prevents concurrent application instances from
applying the same migration simultaneously.

The initial migration creates the current schema using idempotent statements,
so an existing database created by an earlier version of this project can
adopt migration tracking without dropping its tables or measurement data.

After a migration has been committed, do not edit or rename it. To change the
schema, add a new migration file with the next version, such as
`0002_add_station_metadata.sql`. This preserves a consistent upgrade path for
existing installations.

### Database design

The database follows a normalized dimensional design consisting of one
fact table and two dimension tables.

This design was chosen to reduce data redundancy, improve data integrity,
and make it easier to extend the solution with additional environmental
measurement types in the future.

#### Dimension tables

##### DIM_SOURCES

Stores metadata describing each measurement source.

Examples:

- DMI Observation API
- Future environmental APIs
- Sensor networks

##### DIM_PARAMETERS

Stores metadata describing measurable environmental parameters and
their associated units.

Examples:

| ID | Parameter | Unit |
|----|-----------|------|
| 1 | Temperature | °C |
| 2 | Humidity | % |
| 3 | Humidity Past 1 Hour | % |
| 4 | CO2 | ppm |
| 5 | PM2.5 | μg/m³ |

#### Fact table

##### FACT_MEASUREMENTS

Stores individual environmental observations.

Each measurement references:

- one source
- one parameter

through foreign-key relationships.

The schema also includes a unique constraint on:

```sql
(source_id, parameter_id, timestamp)
```

#### Entity relationship diagram

The ER diagram describes the PostgreSQL data model and the relationships
between its tables.

```mermaid
erDiagram
    DIM_SOURCES ||--o{ FACT_MEASUREMENTS : records
    DIM_PARAMETERS ||--o{ FACT_MEASUREMENTS : classifies

    DIM_SOURCES {
        VARCHAR source_id PK "Unique source identifier"
        VARCHAR source_name "Source name"
        VARCHAR source_type "API, Sensor etc."
    }

    DIM_PARAMETERS {
        INTEGER parameter_id PK "Parameter identifier"
        VARCHAR parameter_name "Temperature, Humidity, CO2..."
        VARCHAR unit "Measurement unit"
    }

    FACT_MEASUREMENTS {
        SERIAL measurement_id PK "Measurement identifier"
        VARCHAR source_id FK "References DIM_SOURCES"
        INTEGER parameter_id FK "References DIM_PARAMETERS"
        TIMESTAMPTZ timestamp "Observation time"
        NUMERIC value "Measurement value"
    }
```

- `DIM_SOURCES` stores metadata about each data source, including its name and
  type.
- `DIM_PARAMETERS` defines the measured parameters and their units.
- `FACT_MEASUREMENTS` stores each environmental observation's timestamp and
  numeric value.
- Each measurement references exactly one source and one parameter through
  foreign keys.
- A source and a parameter can each be referenced by multiple measurements.
- Separating measurements from descriptive metadata supports consistent
  storage and analysis across sources and parameters.

---

## Learning objectives

After completing this project, participants should be able to:

- **Apply ETL principles:** separate extraction, transformation, and loading
  responsibilities.
- **Integrate external APIs:** process API responses and handle missing,
  unexpected, or erroneous data.
- **Design comparable data models:** structure measurements from multiple
  sources and justify the schema.
- **Use PostgreSQL:** configure a database and write data from application code.
- **Build reliable pipelines:** support repeated runs without duplicate or
  destructive writes.
- **Test integrations effectively:** isolate external services in unit tests
  and target at least 95% test coverage.
- **Plan for data reuse:** consider how collection choices support future
  analysis, including workplace environmental quality.
- **Deliver professionally:** maintain the remote repository and document
  setup, build, testing, execution, architecture, and UML in the README.

---

## Author

**Mie Louise Nielsen**

GitHub: https://github.com/mielouise


---

## Runde 2: architecture and operations

The application now exposes one concrete orchestration function, `run_weather_pipeline()`, rather than requiring every pipeline to follow a one-source/one-transform/one-destination pattern. Station metadata is loaded before weather measurements; observations are fetched separately for each requested meteorological parameter. Transformations are split into small functions and placed in `app/transform_steps/`, while persistence is in `app/loaders/`. Legacy imports are kept for compatibility.

```mermaid
flowchart TD
    Main[main: single run or periodic poll] --> Pipeline[run_weather_pipeline]
    Pipeline --> Stations[extract/stations.py]
    Pipeline --> Observations[extract/dmi.py]
    Stations --> StationTransform[transform_steps/stations.py]
    Observations --> MeasurementTransform[transform_steps/observations.py]
    StationTransform --> StationLoad[loaders: save_stations]
    StationLoad --> MeasurementLoad[loaders: save_measurements]
    MeasurementTransform --> MeasurementLoad
    MeasurementLoad --> Database[(PostgreSQL)]
```

The connection helpers remain in `app/database.py`, whereas migration tracking, SHA-256 checksums, transaction handling and advisory locking have moved to `app/migration_runner.py`. SQL migration `0001_initial_schema.sql` is unchanged. The new `0002_add_stations.sql` adds a station dimension and a nullable station foreign key to the fact table. The uniqueness key now contains `station_id` to prevent observations from different stations overwriting each other. Missing station IDs in historical records stay NULL; station IDs not returned by the station endpoint are still retained as minimal dimension records.

### Environment configuration

| Variable | Default | Purpose |
|---|---|---|
| `DMI_API_URL` | Meteorological observations endpoint (in Compose) | Observations items endpoint |
| `DMI_STATIONS_URL` | DMI meteorological stations endpoint | Station metadata items endpoint |
| `DMI_PARAMETER_IDS` | `temp_dry,humidity` | Comma-separated requested parameter types |
| `DMI_STATION_ID` | unset | Optional DMI station ID filter |
| `DMI_LOOKBACK_MINUTES` | `60` | Sliding lookback period for late-arriving observations |
| `DMI_PAGE_SIZE` | `1000` | Maximum features requested per page |
| `DMI_POLL_SECONDS` | `0` in Python; `300` in Compose | 0 = run once; greater than 0 = repeat |
| `DMI_FETCH_STATIONS` | `true` | Whether to refresh station metadata |

To run continuously:

```bash
docker compose up --build app
```

For an individual cycle, override `DMI_POLL_SECONDS=0`. To run tests, use:

```bash
docker compose run --build --rm tests
```

The observation client sends `parameterId`, `datetime`, `limit` and `offset` to the DMI API rather than downloading everything and filtering only locally. `stationId` is sent when configured. Overlapping time windows are intentional: database upserts make repeated ingestion idempotent. A per-query safety cap is imposed to prevent runaway pagination. Each request has a network timeout; a failed polling cycle is logged and retried on the next scheduled cycle.

### Parameter selection and limitations

The pre-existing dimension includes `temp_dry`, `humidity`, `humidity_past1h`, `co2` and `pm25`. **Only `temp_dry` and `humidity` are configured by default.** Other internal mappings are retained for compatibility, but the meteorological observation collection does not necessarily provide every mapped environmental variable. Unsupported parameters are not blindly added to the database: each addition requires confirmation of the provider's documented parameter names and units, a matching dimension entry, and tests. This is why the project intentionally does not collect all available DMI measurements.

Stations have geographical point coordinates, and observations reference their IDs. **Historical warning:** a station may change location or metadata over time. The present `dim_stations` table stores one record per station ID, so its coordinates represent the last loaded version, not a time-versioned history. For strict historical location accuracy, extend the schema to station versions with validity intervals and join observations by observation date.

See the existing sections above for installation and the original database design, plus the newer relationships explained here.
