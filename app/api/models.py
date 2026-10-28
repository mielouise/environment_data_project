"""Define public response schemas for the API and OpenAPI documentation."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

type AwareTimestamp = Annotated[datetime, AwareDatetime()]


class ErrorResponse(BaseModel):
    """Describe a missing resource or unavailable database."""

    detail: str


class HealthResponse(BaseModel):
    """Confirm that the API can query its database."""

    status: Literal["ok"]


class Parameter(BaseModel):
    """Describe an imported measurement type and its unit or code."""

    parameter_id: int
    parameter_name: str
    unit: str


class Station(BaseModel):
    """Describe a station or sensor node with metadata when known."""

    station_id: str = Field(description="Station ID or sensor node ID.")
    station_name: str | None
    station_type: str | None
    country_code: str | None
    latitude: float | None = Field(description="WGS84 latitude, if known.")
    longitude: float | None = Field(description="WGS84 longitude, if known.")
    station_height: float | None = Field(description="Height in metres, if known.")
    valid_from: AwareTimestamp | None = Field(
        description="Time from which the metadata is valid, if known."
    )


class Measurement(BaseModel):
    """Represent one stored environmental observation with parameter metadata.

    PostgreSQL numeric values are converted to JSON numbers. Timestamps
    identify the observation time and always include a timezone.
    """

    measurement_id: int
    source_id: str
    source_observation_id: str | None
    source_reading_id: str | None
    station_id: str
    parameter_id: int
    parameter_name: str
    unit: str
    timestamp: AwareTimestamp = Field(
        description="Observation time, including its timezone."
    )
    value: float = Field(
        description="Numeric value in the given unit; enum means a code."
    )


class Page[ItemT](BaseModel):
    """Wrap a result page and indicate whether more items exist.

    ItemT is the response model used by the endpoint, such as Station or
    Measurement. The next page starts at offset + limit.
    """

    items: list[ItemT]
    limit: int
    offset: int
    has_more: bool = Field(description="Request offset + limit to get the next page.")
