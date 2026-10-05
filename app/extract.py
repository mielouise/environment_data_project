# app/extract.py
from abc import ABC, abstractmethod
import requests

class SensorDataSource(ABC):
    """Abstrakt klasse som definerer interfacet for alle datakilder."""
    
    def __init__(self, source_id: str, source_name: str):
        self.source_id = source_id
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> dict | list:
        """Hent rådata fra kilden."""
        pass


class DMIDataSource(SensorDataSource):
    """Specifik implementering til at hente data fra DMI API."""
    
    def __init__(self, source_id: str, source_name: str, url: str):
        super().__init__(source_id, source_name)
        self.url = url

    def fetch(self) -> dict:
        """Kaler DMI API og håndterer netværksfejl."""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Clean code: Kast en sigende fejl fremfor bare at crashe lydløst
            raise RuntimeError(f"Kunne ikke hente data fra DMI: {e}")
