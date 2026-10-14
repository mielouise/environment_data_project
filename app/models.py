"""Records shared by pipeline stages."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class MeasurementDTO:
    source_id: str
    parameter_id: int
    timestamp: datetime
    value: float
    station_id: str | None = None

@dataclass(frozen=True)
class StationDTO:
    source_id: str
    station_id: str
    name: str | None
    longitude: float | None
    latitude: float | None
    metadata: dict[str, Any]
