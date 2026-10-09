"""ETL orchestration service.

Coordinates the complete Extract, Transform, and Load workflow.
"""

from extract import DMIDataSource
from load import MeasurementRepository
from transform import (
    DMIDataTransformer,
    MeasurementDTO,
)


class ETLService:
    """Execute environmental ETL pipeline."""

    def __init__(
        self,
        source: DMIDataSource,
        transformer: DMIDataTransformer,
        repository: MeasurementRepository
    ) -> None:
        """Initialize ETL service."""
        self._source = source
        self._transformer = transformer
        self._repository = repository

    def run(self) -> int:
        """Run the ETL pipeline.

        Returns:
            Number of measurements processed.
        """

        raw_data = self._source.fetch()

        measurements: list[MeasurementDTO] = (
            self._transformer.transform(raw_data)
        )

        self._repository.save_source(
            source_id=self._source.source_id,
            source_name=self._source.source_name,
            source_type="API_DMI"
        )

        self._repository.save_measurements(
            measurements
        )

        return len(measurements)