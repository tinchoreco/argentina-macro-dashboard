"""Time series transformations.

Pure functions that operate on lists of (date, value) observations.
No dependency on pandas — the operations we need are simple enough
that adding pandas would be overkill.
"""

from __future__ import annotations

from datetime import date


def parse_iso_date(s: str) -> date:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    return date.fromisoformat(s)


def monthly_percent_change(
    observations: list[tuple[str, float]],
) -> list[tuple[str, float | None]]:
    """Compute month-over-month percent change.

    For each observation at index i, returns (date_i, 100 * (v_i - v_{i-1}) / v_{i-1}).
    The first observation has None as its variation.

    Args:
        observations: Chronologically sorted (date, value) tuples.

    Returns:
        List of (date, pct_change) tuples, same length as input.
    """
    if not observations:
        return []

    result: list[tuple[str, float | None]] = [(observations[0][0], None)]
    for i in range(1, len(observations)):
        prev_value = observations[i - 1][1]
        curr_date, curr_value = observations[i]
        if prev_value == 0:
            result.append((curr_date, None))
        else:
            change = 100.0 * (curr_value - prev_value) / prev_value
            result.append((curr_date, change))
    return result


def yoy_percent_change(
    observations: list[tuple[str, float]],
) -> list[tuple[str, float | None]]:
    """Compute year-over-year percent change for a monthly series.

    Matches each observation with the one exactly 12 months earlier.
    Returns None for the first 12 observations (no comparable base).

    Args:
        observations: Chronologically sorted (date, value) tuples,
            assumed to be monthly data.

    Returns:
        List of (date, pct_change) tuples, same length as input.
    """
    if not observations:
        return []

    # Build an index by (year, month) for O(1) lookup.
    by_year_month: dict[tuple[int, int], float] = {}
    for date_str, value in observations:
        d = parse_iso_date(date_str)
        by_year_month[(d.year, d.month)] = value

    result: list[tuple[str, float | None]] = []
    for date_str, value in observations:
        d = parse_iso_date(date_str)
        prev_key = (d.year - 1, d.month)
        prev_value = by_year_month.get(prev_key)
        if prev_value is None or prev_value == 0:
            result.append((date_str, None))
        else:
            change = 100.0 * (value - prev_value) / prev_value
            result.append((date_str, change))
    return result


def latest_n(
    observations: list[tuple[str, float]],
    n: int,
) -> list[tuple[str, float]]:
    """Return the last N observations (tail of the series).

    If n >= len(observations), returns all of them.
    """
    if n <= 0:
        return []
    return observations[-n:]


def summary_stats(observations: list[tuple[str, float]]) -> dict[str, float | None]:
    """Compute basic headline stats used by the dashboard cards.

    Returns a dict with:
        - last_value: most recent value
        - last_date: most recent date (ISO string)
        - last_mom: month-over-month % change of last observation
        - last_yoy: year-over-year % change of last observation
    All numeric fields may be None if the series is too short.
    """
    if not observations:
        return {
            "last_value": None,
            "last_date": None,
            "last_mom": None,
            "last_yoy": None,
        }

    last_date, last_value = observations[-1]
    mom_series = monthly_percent_change(observations)
    yoy_series = yoy_percent_change(observations)

    return {
        "last_value": last_value,
        "last_date": last_date,
        "last_mom": mom_series[-1][1] if mom_series else None,
        "last_yoy": yoy_series[-1][1] if yoy_series else None,
    }
