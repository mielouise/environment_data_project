"""Run once or poll DMI continuously with bounded UTC windows."""
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from app.database import get_db_connection
from app.migrations import create_tables
from app.extract import DMIDataSource
from app.load import MeasurementRepository
from app.pipeline import run_dmi_pipeline
from app.transform.dmi import DMI_PARAMETERS

def run(*, continuous=False, interval=300, lookback=3600):
    endpoint = os.environ.get('DMI_API_URL')
    if not endpoint:
        raise RuntimeError('DMI_API_URL environment variable is missing.')
    if not all(math.isfinite(n) and n > 0 for n in (interval, lookback)):
        raise ValueError('Polling interval and lookback must be positive finite seconds.')
    parameters = tuple(p.strip() for p in os.environ.get('DMI_PARAMETERS', ','.join(DMI_PARAMETERS)).split(',') if p.strip())
    if not parameters or set(parameters) - set(DMI_PARAMETERS):
        raise ValueError('DMI_PARAMETERS must contain supported DMI parameter IDs.')
    create_tables()
    source = DMIDataSource('DMI', 'DMI Observation API', endpoint)
    # Preserve URL filters, while each cycle explicitly owns its datetime window.
    from urllib.parse import urlsplit, parse_qsl
    filters = dict(parse_qsl(urlsplit(endpoint).query))
    filters.pop('parameterId', None)
    for variable, key in [('DMI_STATION_ID', 'stationId'), ('DMI_BBOX', 'bbox')]:
        if os.environ.get(variable):
            filters[key] = os.environ[variable]
    filters.setdefault('limit', 1000)
    cursor = datetime.now(timezone.utc) - timedelta(seconds=lookback)
    while True:
        end = datetime.now(timezone.utc)
        query = dict(filters)
        if 'datetime' not in filters or continuous:
            query.pop('period', None)
            query['datetime'] = f'{cursor.isoformat()}/{end.isoformat()}'
        connection = None
        try:
            connection = get_db_connection()
            count = run_dmi_pipeline(source, MeasurementRepository(connection), parameters=parameters, filters=query)
            print(f'Successfully processed {count} measurements.', flush=True)
            # Advance only after success. Overlap captures delayed observations.
            cursor = end - timedelta(seconds=lookback)
        except Exception:
            if connection is not None:
                connection.rollback()
            if not continuous:
                raise
            print('Pipeline cycle failed; retrying the same window.', file=sys.stderr, flush=True)
        finally:
            if connection is not None:
                connection.close()
        if not continuous:
            return
        time.sleep(interval)

def main():
    try:
        run(continuous=os.environ.get('ETL_CONTINUOUS', 'false').lower() in ('true', '1', 'yes'),
            interval=float(os.environ.get('ETL_INTERVAL_SECONDS', '300')),
            lookback=float(os.environ.get('DMI_LOOKBACK_SECONDS', '3600')))
    except KeyboardInterrupt:
        print('Pipeline stopped.', flush=True)
    except Exception as err:
        print(f'Pipeline execution failed: {err}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
