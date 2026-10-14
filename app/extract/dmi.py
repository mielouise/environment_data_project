"""DMI Observation API data source."""

from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests

from app.extract.base import SensorDataSource

DMI_COLLECTIONS_PATH = "/v2/metObs/collections"


def build_dmi_collection_url(api_base_url: str, collection: str) -> str:
    """Build a versioned DMI collection endpoint from its API base URL.

    A previously configured collection endpoint is normalized back to its
    deployment base before the requested collection path is appended.

    Args:
        api_base_url: Base URL of the DMI API deployment.
        collection: Supported collection name.

    Returns:
        The collection's feature-items endpoint URL.

    Raises:
        ValueError: If the collection is not supported.
        ValueError: If the base URL is not an HTTP(S) URL.
    """
    if collection not in {"observation", "station"}:
        raise ValueError(f"Unsupported DMI collection: {collection}")
    parsed_url = urlsplit(api_base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("DMI API base URL must be an absolute HTTP(S) URL.")
    if parsed_url.query or parsed_url.fragment:
        raise ValueError(
            "DMI API base URL must not contain a query or fragment."
        )
    base_path = parsed_url.path.rstrip("/")
    endpoint_suffixes = (
        f"{DMI_COLLECTIONS_PATH}/{name}/items"
        for name in ("observation", "station")
    )
    for suffix in (*endpoint_suffixes, DMI_COLLECTIONS_PATH):
        if base_path.endswith(suffix):
            base_path = base_path[: -len(suffix)]
            break

    normalized_base_url = urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            base_path.rstrip("/"),
            "",
            "",
        )
    )
    return (
        f"{normalized_base_url}"
        f"{DMI_COLLECTIONS_PATH}/{collection}/items"
    )


class DMIDataSource(SensorDataSource):
    """Client for the DMI Meteorological Observation API."""

    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str
    ) -> None:
        """Initialize the DMI data source.

        Args:
            source_id:
                Unique identifier of the source.

            source_name:
                Human-readable name of the source.

            url:
                DMI Observation API endpoint URL.
        """
        super().__init__(
            source_id=source_id,
            source_name=source_name
        )

        self.url = url

    def fetch(
        self,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        """Retrieve all pages matching the DMI API query.

        Args:
            params: Optional DMI API query parameters.

        Returns:
            Dictionary containing all returned features.

        Raises:
            RuntimeError:
                Raised when a request fails or the API response is invalid.
        """
        features = []
        page_url = self.url
        page_params = params
        visited_urls = set()
        first_page: dict[str, Any] | None = None

        try:
            while True:
                request_options: dict[str, Any] = {
                    "timeout": self.REQUEST_TIMEOUT_SECONDS
                }
                if page_params is not None:
                    request_options["params"] = page_params
                response = requests.get(page_url, **request_options)
                response.raise_for_status()
                page = response.json()
                if not isinstance(page, dict) or not isinstance(
                    page.get("features"), list
                ):
                    raise RuntimeError(
                        "DMI API response must contain a features list."
                    )

                if first_page is None:
                    first_page = page
                features.extend(page["features"])

                next_url = next(
                    (
                        link["href"]
                        for link in page.get("links", [])
                        if link.get("rel") == "next"
                    ),
                    None,
                )
                if next_url is None:
                    break
                if next_url in visited_urls:
                    raise RuntimeError(
                        "DMI API returned a repeated pagination link."
                    )
                visited_urls.add(next_url)
                page_url = next_url
                page_params = None
        except requests.RequestException as err:
            raise RuntimeError(
                f"Failed to retrieve DMI data: {err}"
            ) from err

        if first_page is None:
            raise RuntimeError("DMI API returned no response pages.")
        return {**first_page, "features": features}
