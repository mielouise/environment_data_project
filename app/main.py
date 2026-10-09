"""Application entry point.

Starts and executes the environmental ETL pipeline.
"""

import sys

from app.database import (
    create_tables,
    get_db_connection
)
from app.etl_service import ETLService
from app.extract import DMIDataSource
from app.load import MeasurementRepository
from app.transform import DMIDataTransformer


def main() -> None:
    """Run ETL process."""

    print(
        "=== Starting Environmental Data ETL Pipeline ==="
    )

    try:
        create_tables()

        dmi_endpoint = (
            "https://opendataapi.dmi.dk/v2/"
            "metObs/collections/observation/items"
        )

        source = DMIDataSource(
            source_id="DMI",
            source_name="DMI Observation API",
            url=dmi_endpoint
        )

        transformer = DMIDataTransformer(
            source_id=source.source_id
        )

        db_connection = get_db_connection()

        repository = MeasurementRepository(
            db_connection
        )

        etl_service = ETLService(
            source=source,
            transformer=transformer,
            repository=repository
        )

        measurement_count = (
            etl_service.run()
        )

        print(
            f"Successfully processed "
            f"{measurement_count} measurements."
        )

        print(
            "=== ETL Pipeline Completed ==="
        )

    except Exception as err:
        print(
            f"Pipeline execution failed: {err}",
            file=sys.stderr
        )
        sys.exit(1)

    finally:
        try:
            db_connection.close()
        except (NameError, UnboundLocalError):
            pass


if __name__ == "__main__":
    main()