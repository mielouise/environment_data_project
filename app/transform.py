"""Transformation services for environmental observations."""

from datetime import datetime
from typing import Any

from app.constants.parameters import ParameterIds
from app.models.measurement import MeasurementDTO


class DMIDataTransformer:
    """Transform DMI observations into MeasurementDTO objects."""

    PARAMETER_MAPPING: dict[str, int] = {
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
                Source identifier assigned to generated DTOs.
        """
        self.source_id = source_id

    def transform(
        self,
        raw_json: dict[str, Any]
    ) -> list"""Transform raw API payload into DTOs.

        Args:
            raw_json:
                Raw DMI API response.

        Returns:
            Collection of normalized measurements.
        """
        measurements: list[MeasurementDTO] = []

        features = raw_json.get(
            "features",
            []
        )

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
            