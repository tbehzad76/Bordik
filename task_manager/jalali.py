"""Jalali (Solar Hijri) calendar conversion.

Algorithms are a Python port of the well-known jalaali-js implementation.
Gregorian dates are stored in the database; Jalali is only for input/output.
"""

import re
from datetime import date, datetime

from .phones import PERSIAN_DIGITS

_BREAKS = [
    -61,
    9,
    38,
    199,
    426,
    686,
    756,
    818,
    1111,
    1181,
    1210,
    1635,
    2060,
    2097,
    2192,
    2262,
    2324,
    2394,
    2456,
    3178,
]

_GREGORIAN_MIN_YEAR = 1700
_SEPARATORS = re.compile(r"[-.\\]")


def _div(a: int, b: int) -> int:
    """Truncated integer division, matching JavaScript's ~~(a / b)."""
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


def _mod(a: int, b: int) -> int:
    """Remainder with the dividend's sign, matching JavaScript's a - ~~(a/b)*b."""
    return a - _div(a, b) * b


def _jal_cal(jy: int) -> tuple[int, int, int]:
    if jy < _BREAKS[0] or jy > _BREAKS[-1]:
        raise ValueError("invalid Jalali year")

    gy = jy + 621
    leap_j = -14
    jp = _BREAKS[0]
    jump = 0

    for i in range(1, len(_BREAKS)):
        jm = _BREAKS[i]
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm

    n = jy - jp
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1

    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g

    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33

    leap = _mod(_mod(n + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4

    return leap, gy, march


def _g2d(gy: int, gm: int, gd: int) -> int:
    d = (
        _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4)
        + _div(153 * _mod(gm + 9, 12) + 2, 5)
        + gd
        - 34840408
    )
    d = d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752
    return d


def _d2g(jdn: int) -> tuple[int, int, int]:
    j = 4 * jdn + 139361631
    j = j + _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _d2j(jdn: int) -> tuple[int, int, int]:
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _, march = _jal_cal(jy)
    jdn1f = _g2d(gy, 3, march)

    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            jm = 1 + _div(k, 31)
            jd = _mod(k, 31) + 1
            return jy, jm, jd
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1

    jm = 7 + _div(k, 30)
    jd = _mod(k, 30) + 1
    return jy, jm, jd


def gregorian_to_jalali(value: date) -> tuple[int, int, int]:
    return _d2j(_g2d(value.year, value.month, value.day))


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    if not 1 <= jm <= 12:
        raise ValueError("invalid Jalali month")

    _, gy, march = _jal_cal(jy)
    jdn = _g2d(gy, 3, march) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1
    result = date(*_d2g(jdn))

    if gregorian_to_jalali(result) != (jy, jm, jd):
        raise ValueError("invalid Jalali date")
    return result


def is_leap_jalali_year(jy: int) -> bool:
    return _jal_cal(jy)[0] == 0


def format_jalali(value: date | datetime | None, pattern: str = "%Y/%m/%d") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    jy, jm, jd = gregorian_to_jalali(value)
    return pattern.replace("%Y", str(jy)).replace("%m", f"{jm:02d}").replace(
        "%d", f"{jd:02d}"
    )


def format_jalali_datetime(
    value: datetime | None, pattern: str = "%Y/%m/%d %H:%M"
) -> str:
    if value is None:
        return ""
    jalali_part = format_jalali(value.date())
    return f"{jalali_part} {value.hour:02d}:{value.minute:02d}"


def parse_jalali(text: str | None) -> date | None:
    """Parse a Jalali date like 1403/05/12 (Persian digits allowed).

    Gregorian ISO dates (year >= 1700) are accepted as well so the API and
    old saved values keep working.
    """
    if not text:
        return None

    value = str(text).translate(PERSIAN_DIGITS).strip()
    if not value:
        return None

    value = _SEPARATORS.sub("/", value)
    parts = value.split("/")
    if len(parts) != 3 or not all(part.strip().isdigit() for part in parts):
        raise ValueError("invalid date format")

    year, month, day = (int(part) for part in parts)
    if year >= _GREGORIAN_MIN_YEAR:
        return date(year, month, day)
    return jalali_to_gregorian(year, month, day)
