"""Module for transforming raw DMI weather data into structured models.

This module implements the transformation layer of the ETL pipeline, converting
raw API response dictionaries into standardized, type-safe Data Transfer
Objects (DTOs) suitable for database insertion.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MeasurementDTO:
    """Data Transfer Object representing a standardized environmental measurement.

    Attributes:
        source_id: Unique identifier for the measurement source or station.
        timestamp: The exact time the measurement was recorded (timezone-aware).
        temperature: Ambient temperature in degrees Celsius.
        humidity: Relative humidity percentage.
        co2_ppm: Carbon dioxide levels in parts per million (reserved for future).
        particulate_matter_pm25: PM2.5 levels in micrograms per cubic meter.
    """

    source_id: str
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    co2_ppm: Optional[int] = None
    particulate_matter_pm25: Optional[float] = None


class DMIDataTransformer:
    """Transformer responsible for parsing and normalizing DMI GeoJSON responses.

    Ensures that incoming dictionary parameters match the required types and formats
    before being passed down to the database loading layer.
    """

    def __init__(self, source_id: str) -> None:
        """Initializes the transformer with a specific source identifier.

        Args:
            source_id: The ID to tag all transformed measurements with.
        """
        self.source_id = source_id

    def transform(self, raw_json: Dict[str, Any]) -> List[MeasurementDTO]:
        """Parses DMI JSON metadata and extracts structured environmental records.

        Groups multi-parameter responses by their timestamps to maintain tidy
        and simplified dataset entries for comparative metrics.

        Args:
            raw_json: The unvalidated dictionary raw payload fetched from DMI API.

        Returns:
            A list of validated and structured MeasurementDTO objects.
        """
        features: List[Dict[str, Any]] = raw_json.get("features", [])
        grouped_by_time: Dict[str, Dict[str, Any]] = {}

        # First pass: Group parameter variables by their exact observation timestamp
        for feature in features:
            properties = feature.get("properties", {})
            observed_time = properties.get("observed")
            parameter_id = properties.get("parameterId")
            value = properties.get("value")

            if not observed_time or value is None:
                continue

            if observed_time not in grouped_by_time:
                grouped_by_time[observed_time] = {}

            # Aligned to support both standard identifiers and DMI v2 raw mapping values
            if parameter_id in ("temp", "temp_dry"):
                grouped_by_time[observed_time]["temp"] = float(value)
            elif parameter_id in ("rh", "humidity", "humidity_past1h"):
                grouped_by_time[observed_time]["rh"] = float(value)

        # Second pass: Construct type-safe DTOs from grouped parameters
        transformed_records: List[MeasurementDTO] = []
        for time_str, data in grouped_by_time.items():
            # Skip timestamps that do not contain any of our targeted metrics
            if "temp" not in data and "rh" not in data:
                continue
                
            try:
                # Handle standard ISO format and replace Z anchor for timezone safety
                timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                
                dto = MeasurementDTO(
                    source_id=self.source_id,
                    timestamp=timestamp,
                    temperature=data.get("temp"),
                    humidity=data.get("rh")
                )
                transformed_records.append(dto)
            except (ValueError, TypeError) as err:
                # Clean code: Log or skip structurally corrupt individual entries gently
                print(f"Skipping corrupt record timestamp '{time_str}': {err}")
                continue

        return transformed_records
