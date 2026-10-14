"""Legacy compatibility facade. Prefer app.pipelines.weather_pipeline."""
from app.transform import DMIDataTransformer


class ETLService:
    """Backward-compatible adapter; new pipelines use a plain function."""
    def __init__(self, source, transformer, repository):
        self._source = source
        self._transformer = transformer
        self._repository = repository

    def run(self):
        raw = self._source.fetch()
        rows = self._transformer.transform(raw)
        self._repository.save_source(
            self._source.source_id, self._source.source_name, "API_DMI"
        )
        self._repository.save_measurements(rows)
        return len(rows)
