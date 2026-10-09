"""Unit tests for the transformation layer."""

from datetime import datetime, timezone

import pytest

from app.constants.parameters import ParameterIds
from app.transform import (
    DMIDataTransformer,
    MeasurementDTO,
)


def test_transform_temperature() -> None:
    """Verify temp_dry observations are transformed."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

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

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert len(results) == 1

    measurement = results[0]

    assert (
        measurement.parameter_id
        == ParameterIds.HUMIDITY
    )

    assert measurement.value == 85.0


def test_transform_humidity_past_1h() -> None:
    """Verify humidity_past1h maps correctly."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert len(results) == 1

    assert (
        results[0].parameter_id
        == ParameterIds.HUMIDITY_PAST_1H
    )


@pytest.mark.parametrize(
    ("parameter_name", "expected_parameter_id"),
    [
        ("co2", ParameterIds.CO2),
        ("pm25", ParameterIds.PM25),
    ],
)
def test_transform_additional_supported_parameters(
    parameter_name,
    expected_parameter_id,
):
    """Verify all currently supported parameter IDs are mapped."""

    transformer = DMIDataTransformer(source_id="DMI")
    raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": parameter_name,
                    "observed": "2026-10-09T10:00:00Z",
                    "value": "42.5",
                }
            }
        ]
    }

    results = transformer.transform(raw_json)

    assert len(results) == 1
    assert results[0].parameter_id == expected_parameter_id
    assert results[0].value == 42.5


def test_transform_unknown_parameter() -> None:
    """Verify unsupported parameters are ignored."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert results == []


def test_transform_missing_value() -> None:
    """Verify observations without value are ignored."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert results == []


def test_transform_missing_required_observation_fields() -> None:
    """Verify observations missing their parameter or timestamp are ignored."""

    transformer = DMIDataTransformer(source_id="DMI")
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

    assert transformer.transform(raw_json) == []


def test_transform_invalid_timestamp() -> None:
    """Verify invalid timestamps are ignored."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert results == []


def test_transform_invalid_numeric_value() -> None:
    """Verify values that cannot be converted to floats are ignored."""

    transformer = DMIDataTransformer(source_id="DMI")
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

    assert transformer.transform(raw_json) == []


def test_transform_multiple_observations() -> None:
    """Verify multiple observations are transformed."""

    transformer = DMIDataTransformer(
        source_id="DMI"
    )

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

    results = transformer.transform(raw_json)

    assert len(results) == 2

    assert all(
        isinstance(
            measurement,
            MeasurementDTO
        )
        for measurement in results
    )