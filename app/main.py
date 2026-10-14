"""Application entry point for a one-shot or continuously scheduled DMI pipeline."""
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from app.database import create_tables, get_db_connection
from app.extract import DMIDataSource
from app.extract.stations import DMIStationSource
from app.load import MeasurementRepository
from app.pipelines.weather_pipeline import run_weather_pipeline

logger = logging.getLogger(__name__)


def run_once() -> int:
    """Run one cycle and close database connection even on failure."""
    url = os.environ.get("DMI_API_URL")
    if not url:
        raise RuntimeError("DMI_API_URL environment variable is missing.")
    create_tables()
    interval_minutes = int(os.environ.get("DMI_LOOKBACK_MINUTES", "60"))
    start = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes)
    params = {
        "datetime": start.isoformat().replace("+00:00", "Z") + "/..",
        "limit": int(os.environ.get("DMI_PAGE_SIZE", "1000")),
    }
    parameter = os.environ.get("DMI_PARAMETER_ID", "temp_dry")
    if parameter:
        params["parameterId"] = parameter

    station_ids = os.environ.get("DMI_STATION_ID")
    if station_ids:
        params["stationId"] = station_ids
    source = DMIDataSource("DMI", "DMI Observation API", url)
    station_url = os.environ.get(
        "DMI_STATIONS_URL", "https://opendataapi.dmi.dk/v2/metObs/collections/station/items"
    )
    station_source = DMIStationSource("DMI_STATIONS", "DMI Station API", station_url)
    connection = get_db_connection()
    try:
        repo = MeasurementRepository(connection)
        return run_weather_pipeline(source, repo, station_source=station_source, params=params)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    """Run once by default; enable polling with DMI_POLL_SECONDS."""
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
