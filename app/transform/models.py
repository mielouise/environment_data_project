"""Data models shared by transformation and persistence stages."""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

RecordT = TypeVar("RecordT")


@dataclass(frozen=True)
class TransformResult(Generic[RecordT]):
    """Transformed records and counts grouped by skip reason."""

    records: list[RecordT]
    skipped: dict[str, int]

    @property
    def input_count(self) -> int:
        """Return the number of input records represented in this result."""
        return len(self.records) + sum(self.skipped.values())


@dataclass(frozen=True)
class MeasurementDTO:
    """A normalized environmental measurement."""

    source_id: str
    station_id: str
    parameter_id: int
    timestamp: datetime
    value: float


@dataclass(frozen=True)
class StationDTO:
    """A DMI station and its latest known location."""

    station_id: str
    name: str
    station_type: str
    country_code: str
    latitude: float
    longitude: float
    station_height: float | None
    valid_from: datetime
