"""Data models shared by transformation and persistence stages."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TransformResult[RecordT]:
    """Transformed records and counts grouped by skip reason."""

    records: list[RecordT]
    skipped: dict[str, int]

    @property
    def input_count(self) -> int:
        """Return the number of input records represented in this result."""
        return len(self.records) + sum(self.skipped.values())


@dataclass(frozen=True)
class MeasurementDTO:
    """A normalized environmental measurement and optional source identities."""

    source_id: str
    station_id: str
    parameter_id: int
    timestamp: datetime
    value: float
    source_observation_id: str | None = None
    source_reading_id: str | None = None


@dataclass(frozen=True)
class StationDTO:
    """A station or sensor node with metadata when it is available."""

    station_id: str
    name: str | None
    station_type: str | None
    country_code: str | None
    latitude: float | None
    longitude: float | None
    station_height: float | None
    valid_from: datetime | None
