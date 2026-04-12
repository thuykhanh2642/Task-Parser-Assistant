from __future__ import annotations

import re
from typing import Any

_TRAILING_PUNCTUATION = re.compile(r"\s*[,;:\-]+\s*$")
_LEADING_PUNCTUATION = re.compile(r"^\s*[,;:\-]+\s*")
_DOUBLED_PUNCTUATION = re.compile(r"\s*[,;:\-]+\s*[,;:\-]+\s*")
_TIME_PREPOSITIONS = ("at", "by", "before")
_DATE_PREPOSITIONS = ("on", "by", "before")
_LOOSE_SCHEDULING_DATES = (
    "today",
    "tomorrow",
    "tonight",
    "this morning",
    "this afternoon",
    "this evening",
)


def extract_task(text: str, entities: dict[str, Any] | None = None) -> str | None:
    if not text:
        return None

    task_text = text
    if entities:
        date = entities.get("date")
        time = entities.get("time")

        if isinstance(time, str):
            task_text = _remove_adjoined_entity(task_text, time, _TIME_PREPOSITIONS)

        if isinstance(date, str):
            task_text = _remove_adjoined_entity(task_text, date, _DATE_PREPOSITIONS)
            if isinstance(time, str) and _is_specific_time(time) and date.lower() in _LOOSE_SCHEDULING_DATES:
                task_text = _remove_loose_date_aside(task_text, date)

    task_text = _TRAILING_PUNCTUATION.sub("", task_text)
    task_text = _LEADING_PUNCTUATION.sub("", task_text)
    task_text = _DOUBLED_PUNCTUATION.sub(" ", task_text)
    task_text = re.sub(r"\s+", " ", task_text).strip()
    return task_text or None


def _remove_adjoined_entity(text: str, value: str, prepositions: tuple[str, ...]) -> str:
    prep_group = "|".join(prepositions)
    pattern = rf"(?P<prefix>\s|^)(?:{prep_group})\s+{re.escape(value)}(?=[\s,.;!?]|$)"
    return re.sub(pattern, _collapse_prefix, text, count=1, flags=re.IGNORECASE)


def _remove_loose_date_aside(text: str, value: str) -> str:
    pattern = rf"(?P<prefix>\s|^){re.escape(value)}(?=[\s,.;!?]|$)"
    return re.sub(pattern, _collapse_prefix, text, count=1, flags=re.IGNORECASE)


def _is_specific_time(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(
        re.fullmatch(r"\d{1,2}:\d{2}\s?(?:am|pm)?", normalized)
        or re.fullmatch(r"\d{1,2}\s?(?:am|pm)", normalized)
        or normalized in {"noon", "midnight"}
    )


def _collapse_prefix(match: re.Match[str]) -> str:
    return "" if match.group("prefix") == "" else " "
