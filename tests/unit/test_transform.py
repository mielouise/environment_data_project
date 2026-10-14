"""Unit tests for the transformation functions."""

from datetime import datetime, timezone

import pytest

from app.constants.parameters import ParameterIds
from app.transform import (
    MeasurementDTO,
    transform_dmi_observations,
    transform_dmi_observations_with_report,
)
from app.transform.dmi import PARAMETER_MAPPING


def _observation(parameter_name, value=15.5, observed="2026-10-09T10:00:00Z"):
    return {
        "properties": {
            "parameterId": parameter_name,
            "observed": observed,
            "stationId": "05329",
            "value": value,
        }
    }


def test_transform_temperature():
    results = transform_dmi_observations(
        {"features": [_observation("temp_dry")]},
        source_id="DMI",
    )

    assert results == [
        MeasurementDTO(
            source_id="DMI",
            station_id="05329",
            parameter_id=ParameterIds.TEMPERATURE.value,
            timestamp=datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
            value=15.5,
        )
    ]


@pytest.mark.parametrize(
    ("parameter_name", "expected_parameter_id"),
    [
        ("humidity", ParameterIds.HUMIDITY),
        ("humidity_past1h", ParameterIds.HUMIDITY_PAST_1H),
    ],
)
def test_transform_supported_parameters(
    parameter_name,
    expected_parameter_id,
):
    results = transform_dmi_observations(
        {"features": [_observation(parameter_name, "42.5")]},
        source_id="DMI",
    )

    assert len(results) == 1
    assert results[0].parameter_id == expected_parameter_id.value
    assert results[0].value == 42.5


def test_transform_all_documented_dmi_parameters():
    features = [
        _observation(parameter_name, value="1")
        for parameter_name in PARAMETER_MAPPING
    ]

    results = transform_dmi_observations(
        {"features": features},
        source_id="DMI",
    )

    assert len(results) == len(PARAMETER_MAPPING)
    assert {
        result.parameter_id for result in results
    } == {
        parameter.value for parameter in PARAMETER_MAPPING.values()
    }


def test_transform_categorical_dmi_codes_as_numeric_values():
    results = transform_dmi_observations(
        {
            "features": [
                _observation("weather", 171),
                _observation("snow_cover_man", 0),
            ]
        },
        source_id="DMI",
    )

    assert [result.value for result in results] == [171.0, 0.0]


@pytest.mark.parametrize(
    "feature",
    [
        _observation("unknown_parameter"),
        _observation("co2"),
        _observation("pm25"),
        _observation("temp_dry", None),
        _observation("temp_dry", observed="NOT_A_DATE"),
        _observation("temp_dry", "not-a-number"),
        {"properties": {"observed": "2026-10-09T10:00:00Z", "value": 1}},
        {"properties": {"parameterId": "temp_dry", "value": 1}},
    ],
)
def test_unsupported_or_invalid_observations_are_skipped(feature):
    assert transform_dmi_observations(
        {"features": [feature]},
        source_id="DMI",
    ) == []


def test_observation_transform_report_counts_skips_by_reason():
    report = transform_dmi_observations_with_report(
        {
            "features": [
                _observation("temp_dry"),
                {"properties": {"parameterId": "temp_dry"}},
                _observation("unknown_parameter"),
                _observation("temp_dry", observed="NOT_A_DATE"),
                _observation("temp_dry", "not-a-number"),
            ]
        },
        source_id="DMI",
    )

    assert len(report.records) == 1
    assert report.input_count == 5
    assert report.skipped == {
        "missing_required_fields": 1,
        "unsupported_parameter": 1,
        "invalid_timestamp": 1,
        "invalid_value": 1,
    }


def test_transform_multiple_observations():
    results = transform_dmi_observations(
        {
            "features": [
                _observation("temp_dry", 15),
                _observation("humidity", 72),
            ]
        },
        source_id="DMI",
    )

    assert len(results) == 2
    assert all(isinstance(result, MeasurementDTO) for result in results)
