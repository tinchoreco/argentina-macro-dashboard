"""Client for the datos.gob.ar time series API.

Wraps HTTP calls to https://apis.datos.gob.ar/series/api/series/ with
retry logic, explicit error handling, and a normalized output structure.

API docs: https://datosgobar.github.io/series-tiempo-ar-api/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = "https://apis.datos.gob.ar/series/api/series/"
DEFAULT_TIMEOUT = 30  # seconds
MAX_IDS_PER_REQUEST = 40  # API hard limit


class APIError(Exception):
    """Raised when the API returns an error or the request fails."""


@dataclass
class SeriesData:
    """Normalized container for a single time series fetched from the API.

    Attributes:
        series_id: The original API identifier (e.g. "148.3_INIVELNAL_DICI_M_26").
        observations: List of (date_iso, value) tuples in chronological order.
        metadata: Raw metadata dict from the API response, if requested.
    """

    series_id: str
    observations: list[tuple[str, float]]
    metadata: dict[str, Any] | None = None


class SeriesAPIClient:
    """HTTP client for the Argentina time series API.

    Usage:
        client = SeriesAPIClient()
        series = client.fetch(["148.3_INIVELNAL_DICI_M_26"], start_date="2020-01-01")
    """

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "argentina-macro-dashboard/0.1 (+etl)"}
        )

    def fetch(
        self,
        ids: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        representation_mode: str | None = None,
        collapse: str | None = None,
        limit: int = 5000,
        include_metadata: bool = True,
    ) -> dict[str, SeriesData]:
        """Fetch one or more series from the API.

        Args:
            ids: List of series identifiers. Max 40 per request (API limit).
            start_date: Optional ISO date (YYYY-MM-DD) to filter observations.
            end_date: Optional ISO date (YYYY-MM-DD) to filter observations.
            representation_mode: Optional transformation applied by the API
                ("percent_change", "percent_change_a_year_ago", etc.).
            collapse: Optional frequency change ("month", "quarter", "year").
            limit: Max observations per series (API cap = 5000).
            include_metadata: If True, request full metadata for each series.

        Returns:
            Dict mapping each input ID to its SeriesData. IDs that the API
            does not recognize are omitted from the result; a warning is logged.

        Raises:
            APIError: On network failure or unexpected response shape.
            ValueError: If more than MAX_IDS_PER_REQUEST ids are passed.
        """
        if not ids:
            return {}
        if len(ids) > MAX_IDS_PER_REQUEST:
            raise ValueError(
                f"API accepts at most {MAX_IDS_PER_REQUEST} ids per request; "
                f"got {len(ids)}. Split the call in batches."
            )

        params: dict[str, str] = {
            "ids": ",".join(ids),
            "limit": str(limit),
            "format": "json",
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if representation_mode:
            params["representation_mode"] = representation_mode
        if collapse:
            params["collapse"] = collapse
        if include_metadata:
            params["metadata"] = "full"

        payload = self._request_with_retry(params)
        return self._parse_response(payload, requested_ids=ids)

    def _request_with_retry(self, params: dict[str, str]) -> dict[str, Any]:
        """Execute GET with exponential backoff on transient failures."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.get(
                    self.base_url, params=params, timeout=self.timeout
                )
                # 4xx usually means bad request (wrong ID, bad params) — don't retry.
                if 400 <= resp.status_code < 500:
                    raise APIError(
                        f"API returned {resp.status_code}: {resp.text[:300]}"
                    )
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                sleep_s = self.backoff_factor ** attempt
                logger.warning(
                    "API call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)
        raise APIError(f"API call failed after {self.max_retries} attempts: {last_exc}")

    @staticmethod
    def _parse_response(
        payload: dict[str, Any], requested_ids: list[str]
    ) -> dict[str, SeriesData]:
        """Convert the raw API payload into a dict of SeriesData.

        The API response has shape:
            {
                "data": [["2024-01-01", 1.23, 4.56, ...], ...],
                "meta": [{...filter...}, {...series1 meta...}, {...series2 meta...}],
                ...
            }
        Column 0 of `data` is the date; columns 1..N correspond to the order
        of IDs in the request. `meta[0]` is filter info; `meta[1:]` align
        positionally with the series columns.
        """
        if "data" not in payload or "meta" not in payload:
            raise APIError(f"Unexpected response shape: keys={list(payload.keys())}")

        data_rows = payload["data"]
        meta_blocks = payload["meta"]

        # meta[0] is global filter metadata; series metadata starts at index 1.
        series_meta = meta_blocks[1:] if len(meta_blocks) > 1 else []

        # The API returns only series it recognized. Map them back by position.
        recognized_ids: list[str] = []
        for block in series_meta:
            field = block.get("field", {}) if isinstance(block, dict) else {}
            sid = field.get("id")
            if sid:
                recognized_ids.append(sid)

        missing = set(requested_ids) - set(recognized_ids)
        if missing:
            logger.warning(
                "API did not return data for %d id(s): %s",
                len(missing),
                sorted(missing),
            )

        result: dict[str, SeriesData] = {}
        for col_idx, sid in enumerate(recognized_ids, start=1):
            observations: list[tuple[str, float]] = []
            for row in data_rows:
                if col_idx >= len(row):
                    continue
                date_str = row[0]
                value = row[col_idx]
                if value is None:
                    continue
                try:
                    observations.append((date_str, float(value)))
                except (TypeError, ValueError):
                    logger.debug("Skipping non-numeric value for %s: %r", sid, value)
                    continue

            meta_dict = series_meta[col_idx - 1] if col_idx - 1 < len(series_meta) else None
            result[sid] = SeriesData(
                series_id=sid,
                observations=observations,
                metadata=meta_dict,
            )

        return result
