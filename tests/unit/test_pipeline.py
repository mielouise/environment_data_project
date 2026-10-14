from unittest.mock import MagicMock
import pytest
from app.pipeline import run_dmi_pipeline

def observation(station):
    return {'properties': {'stationId': station, 'parameterId': 'temp_dry',
                            'observed': '2026-10-14T10:00:00Z', 'value': 15}}

def test_stations_remain_distinct_and_missing_metadata_is_preserved():
    source, repository = MagicMock(), MagicMock()
    source.source_id = 'DMI'
    source.source_name = 'DMI'
    source.fetch_stations.return_value = {'features': []}
    source.fetch.return_value = {'features': [observation('06101'), observation('06102')]}
    assert run_dmi_pipeline(source, repository, parameters=['temp_dry'], filters={'stationId': '06101'}) == 2
    source.fetch.assert_called_once_with({'stationId': '06101', 'parameterId': 'temp_dry'})
    assert {r.station_id for r in repository.save_measurements.call_args.args[0]} == {'06101', '06102'}
    assert len(repository.save_stations.call_args.args[0]) == 2

def test_fetch_failure_causes_no_writes():
    source, repository = MagicMock(), MagicMock()
    source.fetch_stations.side_effect = RuntimeError('offline')
    with pytest.raises(RuntimeError):
        run_dmi_pipeline(source, repository)
    assert repository.mock_calls == []

def test_missing_station_rejected_before_writes():
    source, repository = MagicMock(), MagicMock()
    source.fetch_stations.return_value = {'features': []}
    feature = observation('06101')
    del feature['properties']['stationId']
    source.fetch.return_value = {'features': [feature]}
    with pytest.raises(ValueError, match='stationId'):
        run_dmi_pipeline(source, repository, parameters=['temp_dry'])
    assert repository.mock_calls == []
