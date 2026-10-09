"""Parameter identifiers used by dim_parameters."""

from enum import IntEnum


class ParameterIds(IntEnum):
    """Parameter identifiers."""

    TEMPERATURE = 1
    HUMIDITY = 2
    HUMIDITY_PAST_1H = 3
    CO2 = 4
    PM25 = 5