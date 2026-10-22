"""Shared enums/labels for priorities and project colors."""

PRIORITIES = ("low", "normal", "high", "urgent")

PRIORITY_LABELS = {
    "low": "کم",
    "normal": "معمولی",
    "high": "زیاد",
    "urgent": "فوری",
}

PRIORITY_ORDER = {
    "urgent": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}

PRIORITY_CLASSES = {
    "low": "priority-low",
    "normal": "priority-normal",
    "high": "priority-high",
    "urgent": "priority-urgent",
}

PROJECT_COLORS = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "purple": "#7c3aed",
    "orange": "#ea580c",
    "rose": "#e11d48",
    "teal": "#0d9488",
    "slate": "#475569",
}

PROJECT_COLOR_SOFT = {
    "blue": "#e6efff",
    "green": "#e5f6ec",
    "purple": "#efe7fe",
    "orange": "#ffefe3",
    "rose": "#ffe7ee",
    "teal": "#e0f5f2",
    "slate": "#eceff3",
}

PROJECT_COLOR_LABELS = {
    "blue": "آبی",
    "green": "سبز",
    "purple": "بنفش",
    "orange": "نارنجی",
    "rose": "صورتی",
    "teal": "فیروزه‌ای",
    "slate": "خاکستری",
}

DEFAULT_PROJECT_COLOR = "blue"


def is_valid_project_color(value: str) -> bool:
    return value in PROJECT_COLORS
