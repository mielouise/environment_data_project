"""Expose stored environmental data through a versioned, read-only REST API.

Run ``uvicorn app.api.main:app --host 127.0.0.1`` to start the API.
Startup applies migrations; dependencies manage database connections;
routes validate filters and return public Pydantic response models.
"""

import logging
from collections.abc import AsyncIterator, Generator, Sequence
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
)
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.models import (
    AwareTimestamp,
    ErrorResponse,
    HealthResponse,
    Measurement,
    Page,
    Parameter,
    Station,
)
from app.api.repository import EnvironmentalReadRepository
from app.database import get_connection
from app.migration_runner import apply_migrations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Apply pending migrations before the API accepts requests.

    Args:
        app: Application instance supplied by FastAPI at startup.

    Yields:
        Control to the running API after database setup completes.

    Raises:
        psycopg.Error: If database setup fails. Startup then stops.
    """
    apply_migrations()
    yield


app = FastAPI(
    title="Environmental Data API",
    version="1.0.0",
    description=(
        "Read DMI and sensor observations stored by the ETL pipelines. "
        "Data is refreshed by running the ETL, not by making API requests. "
        "Start with /api/v1/parameters and /api/v1/stations to discover data."
    ),
    lifespan=lifespan,
    responses={503: {"model": ErrorResponse, "description": "Database unavailable"}},
)


def get_repository() -> Generator[EnvironmentalReadRepository, None, None]:
    """Provide a repository with a read-only transaction.

    Yields:
        A repository available during the request. The context closes
        the connection and rolls back failed transactions.

    Raises:
        psycopg.Error: If connecting or querying fails. The application
            exception handler translates database errors to HTTP 503.
    """
    with get_connection() as connection:
        connection.read_only = True
        yield EnvironmentalReadRepository(connection)


Repository = Annotated[EnvironmentalReadRepository, Depends(get_repository)]
Limit = Annotated[int, Query(ge=1, le=1000, description="Maximum items per page.")]
Offset = Annotated[int, Query(ge=0, description="Number of matching items to skip.")]
router = APIRouter(prefix="/api/v1")


@app.exception_handler(psycopg.Error)
async def database_error_handler(request: Request, exc: psycopg.Error) -> JSONResponse:
    """Translate a database failure to a generic HTTP 503 JSON response.

    Args:
        request: Failed request supplied by FastAPI.
        exc: Database error; only its class name is logged.

    Returns:
        A response omitting SQL, credentials, and connection details.
    """
    logger.error("Database request failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Please try again later."},
    )


@app.get("/", include_in_schema=False)
def documentation() -> RedirectResponse:
    """Redirect the API root to Swagger documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"], response_model=HealthResponse)
def health(repository: Repository) -> HealthResponse:
    """Check that the API can query PostgreSQL."""
    repository.check_connection()
    return HealthResponse(status="ok")


@router.get("/parameters", tags=["Parameters"], response_model=list[Parameter])
def parameters(
    repository: Repository,
    source_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
) -> list[Parameter]:
    """List parameter IDs and units with imported measurements."""
    return repository.list_parameters(source_id=source_id)


@router.get("/stations", tags=["Stations"], response_model=Page[Station])
def stations(
    repository: Repository, limit: Limit = 100, offset: Offset = 0
) -> Page[Station]:
    """List imported station metadata in station ID order.

    Args:
        repository: Injected read-only repository.
        limit: Maximum stations in the response, between 1 and 1000.
        offset: Number of station rows to skip.

    Returns:
        A station page indicating whether more results exist.
    """
    rows = repository.list_stations(limit=limit + 1, offset=offset)
    return _page(rows, limit, offset)


@router.get(
    "/stations/{station_id}",
    tags=["Stations"],
    response_model=Station,
    responses={404: {"model": ErrorResponse, "description": "Station not found"}},
)
def station(
    station_id: Annotated[str, Path(min_length=1, max_length=50)],
    repository: Repository,
) -> Station:
    """Get one station, preserving leading zeros in its ID.

    Args:
        station_id: Station or sensor node identifier, treated as text.
        repository: Injected read-only repository.

    Returns:
        The station's latest imported metadata and location.

    Raises:
        HTTPException: HTTP 404 when the station has not been imported.
    """
    row = repository.get_station(station_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Station not found.")
    return row


@router.get("/measurements", tags=["Measurements"], response_model=Page[Measurement])
def measurements(
    repository: Repository,
    source_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    station_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    parameter_id: Annotated[
        int | None,
        Query(ge=1, description="Database ID from /api/v1/parameters."),
    ] = None,
    start: Annotated[
        AwareTimestamp | None,
        Query(description="Inclusive start; ISO 8601 with timezone."),
    ] = None,
    end: Annotated[
        AwareTimestamp | None,
        Query(description="Inclusive end; ISO 8601 with timezone."),
    ] = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> Page[Measurement]:
    """List environmental measurements, newest first, with optional filters.

    Args:
        repository: Injected read-only repository.
        source_id: Source ID, or None to include every source.
        station_id: Station or sensor node ID, or None for all stations.
        parameter_id: Database parameter ID, or None for all types.
        start: Inclusive earliest timestamp, including a timezone.
        end: Inclusive latest timestamp, including a timezone.
        limit: Maximum measurements in the response, between 1 and 1000.
        offset: Number of matching measurements to skip.

    Returns:
        Measurements with units and pagination metadata.

    Raises:
        HTTPException: HTTP 422 when start is later than end.
    """
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=422, detail="start must be before or equal to end."
        )
    rows = repository.list_measurements(
        source_id=source_id,
        station_id=station_id,
        parameter_id=parameter_id,
        start=start,
        end=end,
        limit=limit + 1,
        offset=offset,
    )
    return _page(rows, limit, offset)


@router.get(
    "/measurements/{measurement_id}",
    tags=["Measurements"],
    response_model=Measurement,
    responses={404: {"model": ErrorResponse, "description": "Measurement not found"}},
)
def measurement(
    measurement_id: Annotated[int, Path(ge=1)], repository: Repository
) -> Measurement:
    """Get one measurement with its parameter name and unit.

    Args:
        measurement_id: Database primary key of the observation.
        repository: Injected read-only repository.

    Returns:
        The stored observation and its parameter metadata.

    Raises:
        HTTPException: HTTP 404 for an unknown ID.
    """
    row = repository.get_measurement(measurement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Measurement not found.")
    return row


def _page[ItemT](rows: Sequence[ItemT], limit: int, offset: int) -> Page[ItemT]:
    """Build a typed response page using one extra row as a lookahead.

    Args:
        rows: Ordered query results containing at most limit + 1 items.
        limit: Maximum number of items to include in the response.
        offset: Number of matching rows skipped by the query.

    Returns:
        A page excluding the extra row but reporting whether it exists.
    """
    return Page[ItemT](
        items=list(rows[:limit]),
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )


app.include_router(router)
