from datetime import date, datetime, timedelta

import pytest

from task_manager.jalali import (
    format_jalali,
    format_jalali_datetime,
    gregorian_to_jalali,
    is_leap_jalali_year,
    jalali_to_gregorian,
    parse_jalali,
)


def test_known_nowruz_dates():
    assert gregorian_to_jalali(date(2024, 3, 20)) == (1403, 1, 1)
    assert gregorian_to_jalali(date(2026, 3, 21)) == (1405, 1, 1)
    assert gregorian_to_jalali(date(2025, 3, 21)) == (1404, 1, 1)
    assert jalali_to_gregorian(1403, 1, 1) == date(2024, 3, 20)


def test_gregorian_jalali_roundtrip():
    start = date(2000, 1, 1)
    for offset in range(0, 8000, 7):
        value = start + timedelta(days=offset)
        jy, jm, jd = gregorian_to_jalali(value)
        assert jalali_to_gregorian(jy, jm, jd) == value


def test_leap_years():
    assert is_leap_jalali_year(1403) is True
    assert is_leap_jalali_year(1404) is False
    assert jalali_to_gregorian(1403, 12, 30) == date(2025, 3, 20)
    with pytest.raises(ValueError):
        jalali_to_gregorian(1404, 12, 30)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1403/05/12", date(2024, 8, 2)),
        ("\u06f1\u06f4\u06f0\u06f3/\u06f0\u06f5/\u06f1\u06f2", date(2024, 8, 2)),
        ("1403-05-12", date(2024, 8, 2)),
        ("1403.5.12", date(2024, 8, 2)),
        ("2030-05-01", date(2030, 5, 1)),
    ],
)
def test_parse_jalali(text, expected):
    assert parse_jalali(text) == expected


def test_parse_jalali_rejects_invalid():
    with pytest.raises(ValueError):
        parse_jalali("1403/13/01")
    with pytest.raises(ValueError):
        parse_jalali("1403/12/30/1")
    assert parse_jalali("") is None
    assert parse_jalali(None) is None


def test_format_helpers():
    assert format_jalali(date(2024, 8, 2)) == "1403/05/12"
    assert format_jalali(None) == ""
    assert format_jalali_datetime(datetime(2024, 8, 2, 14, 5)) == "1403/05/12 14:05"
    assert format_jalali_datetime(None) == ""
