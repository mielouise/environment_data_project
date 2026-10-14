"""Unit tests for the transformation layer."""

from datetime import datetime, timezone

import pytest

from app.constants.parameters import ParameterIds
from app.transform import (
    transform_measurements,
    MeasurementDTO,
)


def test_transform_temperature() -> None:
    """Verify temp_dry observations are transformed."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 15.5,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert len(results) == 1

    measurement = results[0]

    assert measurement.source_id == "DMI"
    assert (
        measurement.parameter_id
        == ParameterIds.TEMPERATURE
    )
    assert measurement.timestamp == datetime(
        2026, 10, 9, 10, 0, tzinfo=timezone.utc
    )
    assert measurement.value == 15.5


def test_transform_humidity() -> None:
    """Verify humidity observations are transformed."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "humidity",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 85.0,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert len(results) == 1

    measurement = results[0]

    assert (
        measurement.parameter_id
        == ParameterIds.HUMIDITY
    )

    assert measurement.value == 85.0


def test_transform_humidity_past_1h() -> None:
    """Verify humidity_past1h maps correctly."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "humidity_past1h",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 81.0,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert len(results) == 1

    assert (
        results[0].parameter_id
        == ParameterIds.HUMIDITY_PAST_1H
    )


@pytest.mark.parametrize("parameter_name", ["co2", "pm25"])
def test_air_quality_parameters_are_not_metobs_observations(parameter_name):
    """These measurements are not part of the selected metObs collection."""
    payload = {"features": [{"properties": {
        "parameterId": parameter_name,
        "observed": "2026-10-09T10:00:00Z",
        "value": 42.5,
    }}]}
    assert transform_measurements(payload, "DMI") == []


def test_transform_unknown_parameter() -> None:
    """Verify unsupported parameters are ignored."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "wind_speed",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 7.5,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert results == []


def test_transform_missing_value() -> None:
    """Verify observations without value are ignored."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": None,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert results == []


def test_transform_missing_required_observation_fields() -> None:
    """Verify observations missing their parameter or timestamp are ignored."""

    raw_json = {
        "features": [
            {
                "properties": {
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 12.5,
                }
            },
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "value": 12.5,
                }
            },
        ]
    }

    assert transform_measurements(raw_json, "DMI") == []


def test_transform_invalid_timestamp() -> None:
    """Verify invalid timestamps are ignored."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "observed": "NOT_A_DATE",
                    "value": 12.5,
                }
            }
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert results == []


def test_transform_invalid_numeric_value() -> None:
    """Verify values that cannot be converted to floats are ignored."""

    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": "not-a-number",
                }
            }
        ]
    }

    assert transform_measurements(raw_json, "DMI") == []


def test_transform_multiple_observations() -> None:
    """Verify multiple observations are transformed."""


    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp_dry",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 15.0,
                }
            },
            {
                "properties": {
                    "parameterId": "humidity",
                    "observed": "2026-10-09T10:00:00Z",
                    "value": 72.0,
                }
            },
        ]
    }

    results = transform_measurements(raw_json, "DMI")

    assert len(results) == 2

    assert all(
        isinstance(
            measurement,
            MeasurementDTO
        )
        for measurement in results
    )