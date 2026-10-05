"""Central orchestration script running the automated environmental ETL workflow.

Initializes database configurations, initiates extraction interfaces, processes records,
and executes transaction loads against the local PostgreSQL container tables.
"""

import sys
from app.database import create_tables, get_db_connection
from app.extract import DMIDataSource
from app.transform import DMIDataTransformer
from app.load import MeasurementRepository


def main() -> None:
    """Executes the sequence tracking logic loop for the environmental datasets."""
    print("=== Starting Environmental Data ETL Pipeline ===")

    # Step 0: Ensure the required PostgreSQL database tables are generated
    try:
        create_tables()
    except Exception as db_err:
        print(f"Critical error initializing schema tables: {db_err}", file=sys.stderr)
        sys.exit(1)

    # Configuration definitions (Fetching standard meteorology stations data)
    dmi_endpoint = (
        "https://dmi.dk"
    )
    station_id = "DMI-STATION-COPENHAGEN"
    station_name = "DMI Copenhagen Main Station"

    # Step 1: Component instantiation applying clean interface decoupled strategies
    source = DMIDataSource(source_id=station_id, source_name=station_name, url=dmi_endpoint)
    transformer = DMIDataTransformer(source_id=station_id)
    
    db_conn = get_db_connection()
    repo = MeasurementRepository(db_connection=db_conn)

    try:
        # Step 2: Extract data from the open-source DMI endpoint
        print(f"Extracting raw data feeds from: {dmi_endpoint}")
        raw_json_payload = source.fetch()

        # Step 3: Transform records into clean normalized data objects
        print("Transforming structural elements into internal storage schemas...")
        clean_records = transformer.transform(raw_json_payload)

        # Step 4: Load configurations and metrics concurrently into Postgres
        print(f"Loading {len(clean_records)} validated items into PostgreSQL...")
        repo.save_source(source.source_id, source.source_name, source_type="API_DMI")
        repo.save_measurements(clean_records)

        print("=== ETL Pipeline Job Successfully Finished ===")

    except RuntimeError as run_err:
        print(f"Pipeline operation execution stopped: {run_err}", file=sys.stderr)
    except Exception as unexpected_err:
        print(f"An unexpected fatal error surfaced: {unexpected_err}", file=sys.stderr)
    finally:
        # Guarantee network connections close smoothly to prevent leaking context resources
        db_conn.close()


if __name__ == "__main__":
    main()
