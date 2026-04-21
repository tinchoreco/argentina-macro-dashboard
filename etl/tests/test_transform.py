"""Tests for etl.transform."""

from __future__ import annotations

import pytest

from etl.transform import (
    latest_n,
    monthly_percent_change,
    summary_stats,
    yoy_percent_change,
)


class TestMonthlyPercentChange:
    def test_empty_returns_empty(self) -> None:
        assert monthly_percent_change([]) == []

    def test_single_observation_returns_none(self) -> None:
        result = monthly_percent_change([("2024-01-01", 100.0)])
        assert result == [("2024-01-01", None)]

    def test_basic_calculation(self) -> None:
        obs = [
            ("2024-01-01", 100.0),
            ("2024-02-01", 110.0),
            ("2024-03-01", 121.0),
        ]
        result = monthly_percent_change(obs)
        assert result[0] == ("2024-01-01", None)
        assert result[1][0] == "2024-02-01"
        assert result[1][1] == pytest.approx(10.0)
        assert result[2][0] == "2024-03-01"
        assert result[2][1] == pytest.approx(10.0)

    def test_negative_change(self) -> None:
        obs = [("2024-01-01", 100.0), ("2024-02-01", 90.0)]
        result = monthly_percent_change(obs)
        assert result[1][1] == pytest.approx(-10.0)

    def test_zero_previous_returns_none(self) -> None:
        obs = [("2024-01-01", 0.0), ("2024-02-01", 50.0)]
        result = monthly_percent_change(obs)
        assert result[1][1] is None


class TestYoYPercentChange:
    def test_empty_returns_empty(self) -> None:
        assert yoy_percent_change([]) == []

    def test_less_than_12_months_all_none(self) -> None:
        obs = [(f"2024-{m:02d}-01", 100.0 + m) for m in range(1, 7)]
        result = yoy_percent_change(obs)
        assert all(v is None for _, v in result)

    def test_exact_12_months_apart(self) -> None:
        obs = [
            ("2024-01-01", 100.0),
            ("2024-02-01", 105.0),
            ("2025-01-01", 200.0),  # 100% YoY vs 2024-01
            ("2025-02-01", 157.5),  # 50% YoY vs 2024-02
        ]
        result = yoy_percent_change(obs)
        assert result[0][1] is None
        assert result[1][1] is None
        assert result[2][1] == pytest.approx(100.0)
        assert result[3][1] == pytest.approx(50.0)

    def test_missing_prior_year_month_returns_none(self) -> None:
        # Gap in series: no Feb 2024, but we have Feb 2025.
        obs = [
            ("2024-01-01", 100.0),
            ("2024-03-01", 110.0),
            ("2025-01-01", 200.0),
            ("2025-02-01", 210.0),  # no 2024-02 to compare
            ("2025-03-01", 220.0),
        ]
        result = yoy_percent_change(obs)
        result_map = dict(result)
        assert result_map["2025-02-01"] is None
        assert result_map["2025-03-01"] == pytest.approx(100.0)


class TestLatestN:
    def test_returns_tail(self) -> None:
        obs = [(f"2024-{m:02d}-01", float(m)) for m in range(1, 13)]
        assert len(latest_n(obs, 3)) == 3
        assert latest_n(obs, 3)[0] == ("2024-10-01", 10.0)
        assert latest_n(obs, 3)[-1] == ("2024-12-01", 12.0)

    def test_n_larger_than_series_returns_all(self) -> None:
        obs = [("2024-01-01", 1.0), ("2024-02-01", 2.0)]
        assert latest_n(obs, 100) == obs

    def test_zero_returns_empty(self) -> None:
        assert latest_n([("2024-01-01", 1.0)], 0) == []


class TestSummaryStats:
    def test_empty_series_all_none(self) -> None:
        stats = summary_stats([])
        assert stats == {
            "last_value": None,
            "last_date": None,
            "last_mom": None,
            "last_yoy": None,
        }

    def test_full_series_computes_everything(self) -> None:
        # 14 months so last obs has both MoM and YoY defined.
        obs = [
            ("2024-01-01", 100.0),
            ("2024-02-01", 102.0),
            ("2024-03-01", 104.0),
            ("2024-04-01", 106.0),
            ("2024-05-01", 108.0),
            ("2024-06-01", 110.0),
            ("2024-07-01", 112.0),
            ("2024-08-01", 114.0),
            ("2024-09-01", 116.0),
            ("2024-10-01", 118.0),
            ("2024-11-01", 120.0),
            ("2024-12-01", 122.0),
            ("2025-01-01", 124.0),
            ("2025-02-01", 127.0),
        ]
        stats = summary_stats(obs)
        assert stats["last_value"] == 127.0
        assert stats["last_date"] == "2025-02-01"
        # MoM: (127 - 124) / 124 * 100
        assert stats["last_mom"] == pytest.approx(100 * 3 / 124)
        # YoY: (127 - 102) / 102 * 100
        assert stats["last_yoy"] == pytest.approx(100 * 25 / 102)
