"""Transformation services for environmental observations.

Transforms raw DMI API observations into normalized Data Transfer
Objects (DTOs) suitable for insertion into the dimensional database.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.constants.parameters import ParameterIds


@dataclass(frozen=True)
class MeasurementDTO:
    """Represents a normalized environmental measurement.

    Attributes:
        source_id:
            Unique identifier of the measurement source.

        parameter_id:
            Foreign key reference to dim_parameters.

        timestamp:
            Timestamp of the observation.

        value:
            Recorded observation value.
    """

    source_id: str
    parameter_id: int
    timestamp: datetime
    value: float


class DMIDataTransformer:
    """Transform DMI observations into MeasurementDTO objects."""

    # Supported DMI parameters and their corresponding
    # identifiers in the dim_parameters dimension table.
    PARAMETER_MAPPING: dict[str, ParameterIds] = {
        "temp_dry": ParameterIds.TEMPERATURE,
        "humidity": ParameterIds.HUMIDITY,
        "humidity_past1h": ParameterIds.HUMIDITY_PAST_1H,
        "co2": ParameterIds.CO2,
        "pm25": ParameterIds.PM25,
    }

    def __init__(
        self,
        source_id: str
    ) -> None:
        """Initialize transformer.

        Args:
            source_id:
                Source identifier assigned to generated measurements.
        """
        self.source_id = source_id

    def transform(
        self,
        raw_json: dict[str, Any]
    ) -> list"""Transform raw DMI observations into DTO objects.

        Extracts supported environmental parameters from the
        DMI API response and converts them into normalized
        MeasurementDTO instances.

        Args:
            raw_json:
                Raw JSON payload returned from the DMI API.

        Returns:
            List of normalized measurements ready for
            persistence in the fact_measurements table.
        """

        measurements: list[MeasurementDTO] = []

        features = raw_json.get("features", [])

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            parameter_name = properties.get(
                "parameterId"
            )

            observed_time = properties.get(
                "observed"
            )

            value = properties.get(
                "value"
            )

            if (
                parameter_name is None
                or observed_time is None
                or value is None
            ):
                continue

            parameter_id = self.PARAMETER_MAPPING.get(
                parameter_name
            )

            if parameter_id is None:
                continue

            try:
                timestamp = datetime.fromisoformat(
                    observed_time.replace(
                        "Z",
                        "+00:00"
                    )
                )

                measurements.append(
                    MeasurementDTO(
                        source_id=self.source_id,
                        parameter_id=int(parameter_id),
                        timestamp=timestamp,
                        value=float(value)
                    )
                )

            except (
                ValueError,
                TypeError,
                AttributeError,
            ):
                continue

        return measurements