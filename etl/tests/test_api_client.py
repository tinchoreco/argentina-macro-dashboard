"""Tests for etl.api_client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses
from responses import matchers

from etl.api_client import (
    API_BASE_URL,
    APIError,
    MAX_IDS_PER_REQUEST,
    SeriesAPIClient,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_response() -> dict:
    with (FIXTURES_DIR / "api_response_ipc.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def client() -> SeriesAPIClient:
    # Zero backoff to keep tests fast.
    return SeriesAPIClient(max_retries=2, backoff_factor=0)


class TestFetch:
    @responses.activate
    def test_fetch_single_series_parses_observations(
        self, client: SeriesAPIClient, sample_response: dict
    ) -> None:
        responses.add(
            responses.GET,
            API_BASE_URL,
            json=sample_response,
            status=200,
        )

        result = client.fetch(
            [
                "148.3_INIVELNAL_DICI_M_26",
                "148.3_INUCLEONAL_DICI_M_22",
            ]
        )

        assert set(result.keys()) == {
            "148.3_INIVELNAL_DICI_M_26",
            "148.3_INUCLEONAL_DICI_M_22",
        }
        nivel_general = result["148.3_INIVELNAL_DICI_M_26"]
        assert len(nivel_general.observations) == 13
        assert nivel_general.observations[0] == ("2024-01-01", 1527.26)
        assert nivel_general.observations[-1] == ("2025-01-01", 2818.20)

    @responses.activate
    def test_fetch_passes_query_params(
        self, client: SeriesAPIClient, sample_response: dict
    ) -> None:
        responses.add(
            responses.GET,
            API_BASE_URL,
            json=sample_response,
            status=200,
            match=[
                matchers.query_param_matcher(
                    {
                        "ids": "148.3_INIVELNAL_DICI_M_26",
                        "limit": "5000",
                        "format": "json",
                        "start_date": "2024-01-01",
                        "metadata": "full",
                    }
                )
            ],
        )

        client.fetch(
            ["148.3_INIVELNAL_DICI_M_26"],
            start_date="2024-01-01",
        )

    def test_empty_ids_returns_empty_dict(self, client: SeriesAPIClient) -> None:
        assert client.fetch([]) == {}

    def test_too_many_ids_raises(self, client: SeriesAPIClient) -> None:
        with pytest.raises(ValueError, match="at most"):
            client.fetch(["id"] * (MAX_IDS_PER_REQUEST + 1))

    @responses.activate
    def test_missing_id_is_logged_not_raised(
        self, client: SeriesAPIClient, sample_response: dict, caplog
    ) -> None:
        # Response only contains 2 series, but we request 3.
        responses.add(responses.GET, API_BASE_URL, json=sample_response, status=200)

        result = client.fetch(
            [
                "148.3_INIVELNAL_DICI_M_26",
                "148.3_INUCLEONAL_DICI_M_22",
                "FAKE_ID_999",
            ]
        )

        assert "FAKE_ID_999" not in result
        assert len(result) == 2
        assert any("FAKE_ID_999" in r.message for r in caplog.records)

    @responses.activate
    def test_4xx_does_not_retry(self, client: SeriesAPIClient) -> None:
        responses.add(
            responses.GET, API_BASE_URL, json={"error": "bad request"}, status=400
        )

        with pytest.raises(APIError, match="400"):
            client.fetch(["some_id"])

        # Only one call, no retries on 4xx.
        assert len(responses.calls) == 1

    @responses.activate
    def test_5xx_retries_then_raises(self, client: SeriesAPIClient) -> None:
        for _ in range(5):
            responses.add(
                responses.GET, API_BASE_URL, json={"error": "server"}, status=500
            )

        with pytest.raises(APIError, match="failed after"):
            client.fetch(["some_id"])

        assert len(responses.calls) == 2  # max_retries=2

    @responses.activate
    def test_5xx_then_success_succeeds(
        self, client: SeriesAPIClient, sample_response: dict
    ) -> None:
        responses.add(responses.GET, API_BASE_URL, json={"e": "e"}, status=503)
        responses.add(responses.GET, API_BASE_URL, json=sample_response, status=200)

        result = client.fetch(["148.3_INIVELNAL_DICI_M_26"])
        assert "148.3_INIVELNAL_DICI_M_26" in result

    @responses.activate
    def test_malformed_response_raises(self, client: SeriesAPIClient) -> None:
        responses.add(
            responses.GET, API_BASE_URL, json={"unexpected": "shape"}, status=200
        )

        with pytest.raises(APIError, match="Unexpected response"):
            client.fetch(["some_id"])
