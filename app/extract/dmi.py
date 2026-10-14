"""DMI client with server-side filtering and complete pagination."""
from urllib.parse import urljoin, urlsplit, parse_qsl
import requests
from app.extract.base import SensorDataSource

class DMIDataSource(SensorDataSource):
    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(self, source_id, source_name, url):
        super().__init__(source_id=source_id, source_name=source_name)
        self.url = url

    def fetch(self, params=None):
        return self.fetch_collection(self.url, params)

    def fetch_stations(self, params=None):
        parts = urlsplit(self.url)
        path = parts.path.rsplit('/collections/', 1)[0] + '/collections/station/items'
        url = parts._replace(path=path, query='', fragment='').geturl()
        # Preserve authentication supplied in the configured URL.
        credentials = {k: v for k, v in parse_qsl(parts.query) if k == 'api-key'}
        return self.fetch_collection(url, {**credentials, **(params or {})})

    def fetch_collection(self, url, params=None):
        features, visited = [], set()
        origin = urlsplit(url)
        try:
            while url:
                if url in visited:
                    raise RuntimeError('DMI pagination repeated a page.')
                visited.add(url)
                kwargs = {'timeout': self.REQUEST_TIMEOUT_SECONDS}
                if params:
                    kwargs['params'] = params
                response = requests.get(url, **kwargs)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
                    raise RuntimeError('Invalid DMI FeatureCollection response.')
                features.extend(payload['features'])
                next_link = next((link['href'] for link in payload.get('links', [])
                                  if link.get('rel') == 'next'), None)
                url = urljoin(url, next_link) if next_link else None
                if url and (urlsplit(url).scheme, urlsplit(url).netloc, urlsplit(url).path) != (origin.scheme, origin.netloc, origin.path):
                    raise RuntimeError('DMI pagination points outside the requested collection.')
                params = None  # The next URL already contains filters and offset.
            return {'features': features}
        except requests.RequestException as err:
            raise RuntimeError('Failed to retrieve DMI data.') from err
