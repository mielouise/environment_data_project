from unittest.mock import MagicMock, patch
import pytest
from app.main import main, run

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('DMI_API_URL', 'https://example.test/collections/observation/items')
    for key in ('ETL_CONTINUOUS', 'DMI_PARAMETERS', 'DMI_STATION_ID', 'DMI_BBOX'):
        monkeypatch.delenv(key, raising=False)

def test_missing_url(monkeypatch):
    monkeypatch.delenv('DMI_API_URL', raising=False)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1

@pytest.mark.usefixtures('configured')
@patch('app.main.create_tables')
@patch('app.main.get_db_connection')
@patch('app.main.run_dmi_pipeline', return_value=2)
def test_one_shot(pipeline, connect, migrations):
    run()
    pipeline.assert_called_once()
    connect.return_value.close.assert_called_once()
    assert 'datetime' in pipeline.call_args.kwargs['filters']

@pytest.mark.usefixtures('configured')
@patch('app.main.create_tables')
@patch('app.main.get_db_connection')
@patch('app.main.run_dmi_pipeline', side_effect=RuntimeError('offline'))
def test_failure_closes_and_rolls_back(pipeline, connect, migrations):
    with pytest.raises(RuntimeError):
        run()
    connect.return_value.rollback.assert_called_once()
    connect.return_value.close.assert_called_once()

@pytest.mark.usefixtures('configured')
@patch('app.main.time.sleep', side_effect=[None, KeyboardInterrupt])
@patch('app.main.create_tables')
@patch('app.main.get_db_connection')
@patch('app.main.run_dmi_pipeline', side_effect=[RuntimeError('offline'), 2])
def test_continuous_retry_keeps_start(pipeline, connect, migrations, sleep):
    with pytest.raises(KeyboardInterrupt):
        run(continuous=True, interval=1)
    assert pipeline.call_count == 2
    windows = [call.kwargs['filters']['datetime'] for call in pipeline.call_args_list]
    assert windows[0].split('/')[0] == windows[1].split('/')[0]
    assert connect.return_value.close.call_count == 2

@pytest.mark.usefixtures('configured')
@pytest.mark.parametrize('interval', [0, -1, float('nan'), float('inf')])
def test_invalid_interval(interval):
    with pytest.raises(ValueError):
        run(interval=interval)
