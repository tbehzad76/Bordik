import re

PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

DEFAULT_COUNTRY_CODE = "98"
_ALLOWED_SEPARATORS = re.compile(r"[\s\-()./]+")


def normalize_phone(raw: str) -> str:
    """Return a canonical phone number like +989121234567.

    Accepts Persian/Arabic digits, spaces, dashes and parentheses. Numbers
    without an international prefix are treated as local numbers of
    DEFAULT_COUNTRY_CODE.
    """
    if raw is None:
        raise ValueError("phone number is required")

    value = str(raw).translate(PERSIAN_DIGITS).strip()
    value = _ALLOWED_SEPARATORS.sub("", value)

    if value.startswith("00"):
        value = "+" + value[2:]

    if value.startswith("+"):
        digits = value[1:]
        if not digits.isdigit():
            raise ValueError("phone number must contain digits only")
    else:
        if not value.isdigit():
            raise ValueError("phone number must contain digits only")
        if value.startswith("0") and len(value) >= 10:
            digits = DEFAULT_COUNTRY_CODE + value[1:]
        elif len(value) == 10 and value.startswith("9"):
            digits = DEFAULT_COUNTRY_CODE + value
        else:
            digits = value

    if not 8 <= len(digits) <= 15:
        raise ValueError("phone number length is invalid")

    return "+" + digits
