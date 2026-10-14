"""Application entry point for the environmental data pipeline."""

import os
import sys

from app.extract import DMIDataSource
from app.extract.dmi import build_dmi_collection_url
from app.migration_runner import apply_migrations
from app.pipeline import run_dmi_pipeline
from app.transform.dmi import SUPPORTED_DMI_PARAMETER_IDS

DEFAULT_DMI_PARAMETER_IDS = (
    "temp_dry",
    "humidity",
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


def main() -> None:
    """Initialize and run one ETL pipeline cycle."""
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

        measurement_count = run_dmi_pipeline(
            observation_source=source,
            station_source=station_source,
            parameter_ids=parameter_ids,
        )
        print(
            f"ETL cycle completed: {measurement_count} observations processed.",
            flush=True,
        )
        print("=== ETL Pipeline Completed ===")
    except Exception as err:  # noqa: BLE001 - CLI boundary reports run failures.
        print(
            f"Pipeline execution failed: {err}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
