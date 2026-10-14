from app.transform import transform_stations


def test_transform_stations_extracts_coordinates():
    payload = {"features": [{"properties": {"stationId": "06030", "name": "Test"},
                               "geometry": {"type": "Point", "coordinates": [12.5, 55.7]}}]}
    assert transform_stations(payload)[0].latitude == 55.7


def test_transform_stations_skips_missing_id():
    assert transform_stations({"features": [{"properties": {}}]}) == []


def test_versions_of_same_station_are_preserved():
    payload = {"features": [
        {"properties": {
            "stationId": "06030", "name": "Old",
            "validFrom": "2019-01-01T00:00:00Z",
            "validTo": "2022-01-01T00:00:00Z",
        }},
        {"properties": {
            "stationId": "06030", "name": "New",
            "validFrom": "2022-01-01T00:00:00Z",
        }},
    ]}
    stations = transform_stations(payload)
    assert len(stations) == 2
    assert stations[0].valid_to == stations[1].valid_from
    assert stations[1].station_name == "New"


def test_station_normalization_handles_invalid_coordinates_and_dates():
    feature = {
        "properties": {
            "stationId": "00999",
            "validFrom": "invalid",
            "validTo": "2026-10-14T00:00:00Z",
            "height": "invalid",
        },
        "geometry": {"type": "Point", "coordinates": ["invalid", 55.7]},
    }
    station = transform_stations({"features": [feature]})[0]
    assert station.latitude == 55.7
    assert station.longitude is None
    assert station.valid_from is None
    assert station.valid_to is not None
    assert station.station_height is None


def test_station_normalization_requires_explicit_timezone():
    from app.transform.stations import parse_utc_timestamp, parse_number
    assert parse_utc_timestamp("2026-01-01T00:00:00") is None
    assert parse_utc_timestamp(None) is None
    assert parse_number(None) is None
