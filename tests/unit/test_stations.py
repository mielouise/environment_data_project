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
