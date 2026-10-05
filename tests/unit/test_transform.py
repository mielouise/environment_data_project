"""Unit tests for the transformation module."""

from datetime import datetime, timezone
from app.transform import DMIDataTransformer, MeasurementDTO


def test_dmi_data_transformer_success():
    """Tests grouping logic and DTO conversions on well-formed payloads."""
    fake_raw_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp",
                    "value": 18.5,
                    "observed": "2026-10-05T12:00:00Z"
                }
            },
            {
                "properties": {
                    "parameterId": "rh",
                    "value": 65.0,
                    "observed": "2026-10-05T12:00:00Z"
                }
            }
        ]
    }
    
    transformer = DMIDataTransformer(source_id="DMI-STATION-01")
    records = transformer.transform(fake_raw_json)

    assert len(records) == 1
    dto = records[0]
    assert isinstance(dto, MeasurementDTO)
    assert dto.source_id == "DMI-STATION-01"
    assert dto.temperature == 18.5
    assert dto.humidity == 65.0
    assert dto.timestamp == datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def test_dmi_data_transformer_corrupt_timestamp():
    """Tests that records with un-parseable timestamps are skipped safely."""
    fake_corrupt_json = {
        "features": [
            {
                "properties": {
                    "parameterId": "temp",
                    "value": 12.0,
                    "observed": "not-a-date"
                }
            }
        ]
    }
    transformer = DMIDataTransformer(source_id="DMI-STATION-01")
    records = transformer.transform(fake_corrupt_json)
    
    assert len(records) == 0
