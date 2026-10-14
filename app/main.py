"""Run one DMI ingestion cycle or poll at a configurable interval."""
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from app.database import create_tables, get_db_connection
from app.extract import DMIDataSource
from app.load import MeasurementRepository
from app.pipelines.weather_pipeline import run_weather_pipeline

logger = logging.getLogger(__name__)


def run_once() -> int:
    """Run migrations and one ETL cycle; always release the database connection."""
    url = os.environ.get("DMI_API_URL")
    if not url:
        raise RuntimeError("DMI_API_URL environment variable is missing.")
    lookback = int(os.environ.get("DMI_LOOKBACK_MINUTES", "60"))
    if lookback < 1:
        raise ValueError("DMI_LOOKBACK_MINUTES must be positive")
    create_tables()

    start = datetime.now(timezone.utc) - timedelta(minutes=lookback)
    configured = os.environ.get("DMI_PARAMETER_IDS", "temp_dry,humidity")
    parameters = [p.strip() for p in configured.split(",") if p.strip()]
    if not parameters:
        raise ValueError("DMI_PARAMETER_IDS requires at least one parameter")
    params = {
        "datetime": start.isoformat().replace("+00:00", "Z") + "/..",
        "limit": int(os.environ.get("DMI_PAGE_SIZE", "1000")),
        "parameterIds": parameters,
    }
    station_filter = os.environ.get("DMI_STATION_ID")
    if station_filter:
        params["stationId"] = station_filter

    source = DMIDataSource("DMI", "DMI Observation API", url)
    station_source = None
    if os.environ.get("DMI_FETCH_STATIONS", "true").lower() in ("1", "true", "yes"):
        station_source = DMIDataSource(
            "DMI_STATIONS", "DMI Station API",
            os.environ.get(
                "DMI_STATIONS_URL",
                "https://opendataapi.dmi.dk/v2/metObs/collections/station/items",
            ),
        )

    connection = get_db_connection()
    try:
        return run_weather_pipeline(
            source, MeasurementRepository(connection),
            station_source=station_source, params=params,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    """Run once by default. Set DMI_POLL_SECONDS to poll continuously."""
    logging.basicConfig(level=logging.INFO)
    try:
        seconds = int(os.environ.get("DMI_POLL_SECONDS", "0"))
        if seconds < 0:
            raise ValueError("DMI_POLL_SECONDS must be nonnegative")
        while True:
            started = time.monotonic()
            try:
                count = run_once()
                logger.info("Processed %s measurements", count)
            except Exception:
                logger.exception("ETL pipeline failed")
                if seconds == 0:
                    raise
            if seconds == 0:
                break
            time.sleep(max(0, seconds - (time.monotonic() - started)))
    except Exception as exc:
        print(f"Pipeline execution failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
