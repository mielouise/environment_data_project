"""Unit tests for Herodot observation transformation."""

from datetime import UTC, datetime

import pytest

from app.constants.parameters import ParameterIds
from app.transform import (
    MeasurementDTO,
    transform_herodot_observations,
    transform_herodot_observations_with_report,
)


def _observation(sensor, value, **overrides):
    observation = {
        "observationId": "observation-123",
        "readingId": "reading-123",
        "nodeId": "node-123",
        "sensor": sensor,
        "instrumentModel": "BME280",
        "timestamp": "2026-10-28T13:00:00Z",
        "value": value,
    }
    observation.update(overrides)
    return observation


@pytest.mark.parametrize(
    ("sensor", "value", "parameter_id", "expected_value"),
    [
        ("temperature", 23.5, ParameterIds.TEMPERATURE, 23.5),
        ("humidity", 51.25, ParameterIds.HUMIDITY, 51.25),
        ("pressure", 101325, ParameterIds.PRESSURE, 1013.25),
        ("co2_concentration", 717, ParameterIds.CO2, 717.0),
    ],
)
def test_transforms_supported_herodot_sensors(
    sensor,
    value,
    parameter_id,
    expected_value,
):
    result = transform_herodot_observations(
        {"observations": [_observation(sensor, value)]}
    )

    assert result == [
        MeasurementDTO(
            source_id="HERODOT",
            station_id="node-123",
            parameter_id=parameter_id.value,
            timestamp=datetime(2026, 10, 28, 13, tzinfo=UTC),
            value=expected_value,
            source_observation_id="observation-123",
            source_reading_id="reading-123",
        )
    ]


def test_ds18b20_without_sensor_name_maps_to_temperature():
    result = transform_herodot_observations(
        {"observations": [_observation("", 18.2, instrumentModel="DS18B20")]}
    )

    assert len(result) == 1
    assert result[0].parameter_id == ParameterIds.TEMPERATURE.value
    assert result[0].source_reading_id == "reading-123"


@pytest.mark.parametrize(
    ("observation", "reason"),
    [
        (None, "invalid_observation"),
        (_observation("temperature", 1, nodeId=None), "missing_node_id"),
        (_observation("temperature", 1, nodeId="x" * 51), "invalid_node_id"),
        (
            _observation("temperature", 1, readingId="r" * 101),
            "invalid_source_identifier",
        ),
        (_observation("", 1, instrumentModel="unknown"), "missing_sensor"),
        (_observation("particulate_matter", 1), "unsupported_sensor"),
        (_observation("temperature", "invalid"), "invalid_value"),
        (_observation("temperature", float("nan")), "invalid_value"),
        (
            _observation("temperature", 1, timestamp="2026-10-28T13:00:00"),
            "invalid_timestamp",
        ),
    ],
)
def test_reports_invalid_or_unsupported_observations(observation, reason):
    report = transform_herodot_observations_with_report({"observations": [observation]})

    assert report.records == []
    assert report.input_count == 1
    assert report.skipped == {reason: 1}


def test_rejects_response_without_observations_list():
    with pytest.raises(ValueError, match="observations list"):
        transform_herodot_observations({})
