# Environment Data Project

A Python-based ETL (Extract, Transform, Load) application that collects weather and environmental data from the Danish Meteorological Institute (DMI) API, processes the data, and stores it in a PostgreSQL database.

This project demonstrates database integration, API consumption, containerized development, automated testing, and object-oriented programming principles.

---

## Features

- Extract weather and environmental data from the DMI API
- Transform raw API responses into a structured format
- Load processed data into PostgreSQL
- Containerized development environment using Docker Compose
- Database management through pgAdmin
- Automated testing with Pytest
- Clean, maintainable, and object-oriented Python code
- Type hints, docstrings, and PEP 8 compliant codebase

---

## Technology Stack

- **Python 3**
- **PostgreSQL**
- **Docker & Docker Compose**
- **Psycopg**
- **Requests**
- **Pytest**
- **pgAdmin**

---

## Architecture

The application retrieves environmental observations from the DMI API,
transforms supported observations into measurement records, and persists them
in PostgreSQL. The diagrams below show the architecture from three different
perspectives: an application component overview, the UML class structure, and
the runtime ETL workflow. Docker, Docker Compose, pgAdmin, and the test runner
are intentionally excluded because they are development or operational tools
rather than application components.

### Application component overview

- Shows the main application components and their responsibilities.
- Shows how the application communicates with the DMI API and PostgreSQL.
- Rendered as a Mermaid flowchart with UML component labels.

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
    Main -.->|initializes schema and opens connection| Database
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
the main ETL path, decision points, error handling, and connection cleanup.

```mermaid
flowchart TD
    Start((Start))
    InitSchema["1. Initialize database schema"]
    ReadURL["2. Read DMI_API_URL"]
    HasURL{"API URL configured?"}
    BuildServices["3. Create data source, transformer,<br/>database connection, repository,<br/>and ETL service"]
    Fetch["4. Fetch observations from DMI API"]
    Transform["5. Transform supported observations<br/>into MeasurementDTO records"]
    SaveSource["6. Save DMI source metadata"]
    SaveMeasurements["7. Call save_measurements(records)"]
    HasRecords{"Any measurements?"}
    WriteRecords["Insert or update measurements<br/>in PostgreSQL"]
    NoRecords["No database writes required"]
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

---

## Project Structure

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

## Getting Started

### Prerequisites

- Git
- Docker Desktop with Docker Compose

### Clone the Repository

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

### Run the tests

Run the complete test suite, including the unit tests and integration tests:

```bash
docker compose run --build --rm tests
```

The test service waits for PostgreSQL to become healthy. Integration tests
connect to the configured PostgreSQL database and make a real request to the
DMI API, so the corresponding environment variables must be configured and
the environment must have network access to DMI.

To run only the unit tests:

```bash
docker compose run --build --rm tests pytest tests/unit
```

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

---


## ETL Workflow

1. Extract data from the DMI API.
2. Transform the data into the required database format.
3. Load the processed data into PostgreSQL.
4. Validate functionality through automated tests.

---

## Database Schema

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

## Learning Objectives

This project was developed to demonstrate:

- REST API integration
- ETL pipeline implementation
- PostgreSQL database design and management
- Docker-based development environments
- Automated testing practices
- Object-oriented Python development

---

## Author

**Mie Louise Nielsen**

GitHub: https://github.com/mielouise