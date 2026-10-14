"""Unit tests for station transformation functions."""

from datetime import datetime, timezone

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
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
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
    assert stations[0].valid_from == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )


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
