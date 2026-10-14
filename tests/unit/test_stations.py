from app.transform import transform_stations


def test_transform_stations_extracts_coordinates():
    payload = {"features": [{"properties": {"stationId": "06030", "name": "Test"},
                               "geometry": {"type": "Point", "coordinates": [12.5, 55.7]}}]}
    assert transform_stations(payload)[0].latitude == 55.7


def test_transform_stations_skips_missing_id():
    assert transform_stations({"features": [{"properties": {}}]}) == []
