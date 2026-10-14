"""Unit tests for station transformation functions."""

from datetime import UTC, datetime

import pytest

from app.transform import (
    StationDTO,
    transform_dmi_stations,
    transform_dmi_stations_with_report,
)


def _station(station_id, valid_from, longitude=8.3327, latitude=55.723):
    return {
        "geometry": {"coordinates": [longitude, latitude]},
        "properties": {
            "stationId": station_id,
            "name": "Outrup",
            "type": "Pluvio",
            "country": "DNK",
            "stationHeight": 18.0,
            "validFrom": valid_from,
        },
    }


def test_transform_station_includes_geojson_location():
    assert transform_dmi_stations(
        {"features": [_station("05329", "2026-01-01T00:00:00Z")]}
    ) == [
        StationDTO(
            station_id="05329",
            name="Outrup",
            station_type="Pluvio",
            country_code="DNK",
            latitude=55.723,
            longitude=8.3327,
            station_height=18.0,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]


def test_transform_stations_keeps_newest_version_per_station():
    stations = transform_dmi_stations(
        {
            "features": [
                _station("05329", "2020-01-01T00:00:00Z"),
                _station(
                    "05329",
                    "2026-01-01T00:00:00Z",
                    longitude=9.0,
                ),
            ]
        }
    )

    assert len(stations) == 1
    assert stations[0].longitude == 9.0
    assert stations[0].valid_from == datetime(2026, 1, 1, tzinfo=UTC)


def test_transform_stations_skips_invalid_locations():
    invalid = _station("invalid", "2026-01-01T00:00:00Z", longitude=181)

    assert transform_dmi_stations({"features": [invalid]}) == []


def test_station_transform_report_counts_invalid_and_old_versions():
    report = transform_dmi_stations_with_report(
        {
            "features": [
                _station("05329", "2020-01-01T00:00:00Z"),
                _station("05329", "2026-01-01T00:00:00Z"),
                _station("bad", "2026-01-01T00:00:00Z", longitude=181),
                {"properties": {}},
            ]
        }
    )

    assert len(report.records) == 1
    assert report.input_count == 4
    assert report.skipped == {
        "superseded_station_version": 1,
        "invalid_coordinates": 1,
        "missing_required_fields": 1,
    }


def test_station_transform_report_counts_invalid_feature_values():
    invalid_height = _station("height", "2026-01-01T00:00:00Z")
    invalid_height["properties"]["stationHeight"] = "unknown"
    invalid_valid_from = _station("date", "not-a-date")
    invalid_coordinates = _station("coordinates", "2026-01-01T00:00:00Z")
    invalid_coordinates["geometry"]["coordinates"][0] = "unknown"

    report = transform_dmi_stations_with_report(
        {
            "features": [
                None,
                {"properties": []},
                invalid_coordinates,
                invalid_height,
                invalid_valid_from,
            ]
        }
    )

    assert report.records == []
    assert report.skipped == {
        "invalid_feature": 1,
        "invalid_properties": 1,
        "invalid_coordinates": 1,
        "invalid_station_height": 1,
        "invalid_valid_from": 1,
    }


def test_station_transform_raises_if_skip_reason_is_missing(monkeypatch):
    monkeypatch.setattr(
        "app.transform.stations._transform_station",
        lambda feature: (None, None),
    )

    with pytest.raises(
        RuntimeError,
        match="Skipped station transformation has no reason",
    ):
        transform_dmi_stations_with_report({"features": [{}]})
