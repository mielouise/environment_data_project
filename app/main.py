"""Application entry point for the environmental data pipeline."""

import argparse
import logging
import math
import os
import sys
import time
from collections.abc import Callable, Sequence
from functools import partial

from app.extract import DMIDataSource
from app.extract.dmi import build_dmi_collection_url
from app.migration_runner import apply_migrations
from app.pipeline import run_dmi_pipeline
from app.transform.dmi import SUPPORTED_DMI_PARAMETER_IDS

DEFAULT_DMI_PARAMETER_IDS = (
    "temp_dry",
    "humidity",
    "wind_speed",
    "precip_past1h",
)


def _configured_parameter_ids() -> tuple[str, ...]:
    """Read and validate the configured DMI parameter selection."""
    configured_ids = os.environ.get("DMI_PARAMETER_IDS")
    if not configured_ids:
        return DEFAULT_DMI_PARAMETER_IDS

    parameter_ids = tuple(
        dict.fromkeys(
            parameter_id.strip()
            for parameter_id in configured_ids.split(",")
            if parameter_id.strip()
        )
    )
    unsupported_ids = set(parameter_ids) - set(SUPPORTED_DMI_PARAMETER_IDS)
    if not parameter_ids or unsupported_ids:
        raise ValueError(
            "DMI_PARAMETER_IDS must contain supported parameter IDs: "
            f"{', '.join(SUPPORTED_DMI_PARAMETER_IDS)}."
        )
    return parameter_ids


def _positive_interval(value: str) -> float:
    """Parse a finite, positive pipeline interval in seconds."""
    try:
        interval = float(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            "interval must be a finite, positive number of seconds"
        ) from err

    if not math.isfinite(interval) or interval <= 0:
        raise argparse.ArgumentTypeError(
            "interval must be a finite, positive number of seconds"
        )
    return interval


def run_continuously(
    run_once: Callable[[], int],
    interval_seconds: float,
) -> None:
    """Run a pipeline repeatedly, reporting failures before retrying."""
    if not math.isfinite(interval_seconds) or interval_seconds <= 0:
        raise ValueError(
            "interval_seconds must be finite and greater than zero."
        )

    while True:
        try:
            measurement_count = run_once()
            print(
                "ETL cycle completed: "
                f"{measurement_count} observations processed.",
                flush=True,
            )
        except Exception:
            logging.exception(
                "Pipeline execution failed; it will be retried."
            )
        time.sleep(interval_seconds)


def main(argv: Sequence[str] = ()) -> None:
    """Initialize and run one-shot or continuous pipeline execution."""
    parser = argparse.ArgumentParser(description="Run the DMI ETL pipeline.")
    parser.add_argument(
        "--interval-seconds",
        type=_positive_interval,
        default=None,
        help=(
            "Repeat the pipeline at this interval. "
            "Defaults to ETL_INTERVAL_SECONDS, or one-shot execution."
        ),
    )
    args = parser.parse_args(argv)
    interval_seconds = args.interval_seconds
    configured_interval = os.environ.get("ETL_INTERVAL_SECONDS")
    if interval_seconds is None and configured_interval:
        try:
            interval_seconds = _positive_interval(configured_interval)
        except argparse.ArgumentTypeError as err:
            parser.error(str(err))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    print("=== Starting Environmental Data ETL Pipeline ===", flush=True)

    try:
        dmi_endpoint = os.environ.get("DMI_API_URL")
        if not dmi_endpoint:
            raise RuntimeError(
                "DMI_API_URL environment variable is missing. Copy "
                ".env.example to .env and set it to the DMI API base URL."
            )

        source = DMIDataSource(
            source_id="DMI",
            source_name="DMI Observation API",
            url=build_dmi_collection_url(dmi_endpoint, "observation"),
        )
        station_source = DMIDataSource(
            source_id="DMI_STATIONS",
            source_name="DMI Observation Stations API",
            url=build_dmi_collection_url(dmi_endpoint, "station"),
        )
        parameter_ids = _configured_parameter_ids()
        apply_migrations()

        run_pipeline = partial(
            run_dmi_pipeline,
            observation_source=source,
            station_source=station_source,
            parameter_ids=parameter_ids,
        )

        if interval_seconds is None:
            measurement_count = run_pipeline()
            print(
                "ETL cycle completed: "
                f"{measurement_count} observations processed.",
                flush=True,
            )
        else:
            logging.info(
                "Continuous execution enabled; interval is %s seconds.",
                interval_seconds,
            )
            run_continuously(run_pipeline, interval_seconds)

        print("=== ETL Pipeline Completed ===")
    except Exception as err:
        print(
            f"Pipeline execution failed: {err}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
