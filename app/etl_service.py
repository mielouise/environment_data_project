"""Deprecated compatibility adapter. New flows use run_weather_pipeline()."""


class ETLService:
    """Preserve existing callers while migrating to function-based orchestration."""
    def __init__(self, source, transformer, repository):
        self._source = source
        self._transformer = transformer
        self._repository = repository

    def run(self):
        raw = self._source.fetch()
        rows = self._transformer.transform(raw)
        self._repository.save_source(
            source_id=self._source.source_id,
            source_name=self._source.source_name,
            source_type="API_DMI",
        )
        self._repository.save_measurements(rows)
        return len(rows)
