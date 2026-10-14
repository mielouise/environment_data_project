"""DMI station endpoint adapter."""
from app.extract.dmi import DMIDataSource


class DMIStationSource(DMIDataSource):
    """Fetch station metadata using the same HTTP handling as observations."""
