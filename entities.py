from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

try:
    import spacy
    from spacy.language import Language
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-light environments
    spacy = None
    Language = Any  # type: ignore[assignment]

_LOCATION_LABELS = {"GPE", "LOC", "FAC", "ORG"}
_DATE_PATTERNS = [
    {"label": "DATE", "pattern": [{"lower": "new"}, {"lower": "year"}, {"lower": "'s"}, {"lower": "eve"}]},
    {"label": "DATE", "pattern": [{"lower": "new"}, {"lower": "years"}, {"lower": "eve"}]},
    {"label": "DATE", "pattern": [{"lower": "christmas"}]},
    {"label": "DATE", "pattern": [{"lower": "thanksgiving"}]},
]
_COMMAND_PATTERNS = [
    {"label": "COMMAND", "pattern": [{"lower": "email"}]},
    {"label": "COMMAND", "pattern": [{"lower": "schedule"}]},
    {"label": "COMMAND", "pattern": [{"lower": "remind"}]},
    {"label": "COMMAND", "pattern": [{"lower": "book"}]},
    {"label": "COMMAND", "pattern": [{"lower": "buy"}]},
    {"label": "COMMAND", "pattern": [{"lower": "call"}]},
]
_CATEGORY_RULES = [
    ("Health", ["gym", "workout", "run", "doctor", "dentist", "prescription", "therapy", "checkup"]),
    ("Work", ["meeting", "manager", "report", "eod", "review", "submit", "deploy", "presentation", "deadline"]),
    ("Errands", ["buy", "store", "groceries", "shop", "pick up", "drop off", "return"]),
    ("Communication", ["email", "call", "message", "text", "send", "reply", "contact"]),
    ("Meeting", ["dinner", "lunch", "standup", "sync", "1-on-1"]),
    ("Finance", ["tax", "invoice", "payment", "budget", "accounting", "bill"]),
]
_TIME_REGEX = re.compile(
    r"\b("
    r"\d{1,2}:\d{2}\s?(?:am|pm)?|"
    r"\d{1,2}\s?(?:am|pm)|"
    r"noon|midnight|"
    r"this morning|this afternoon|this evening|tonight"
    r")\b",
    re.IGNORECASE,
)
_DATE_REGEX = re.compile(
    r"\b("
    r"today|tomorrow|tonight|weekend|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"this\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r")\b",
    re.IGNORECASE,
)
_PERSON_PREP_REGEX = re.compile(r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)")
_PERSON_COMMAND_REGEX = re.compile(
    r"^\s*(?i:email|call|message|text|remind|schedule)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
)
_LEADING_COMMAND_IN_PERSON_REGEX = re.compile(
    r"^(?i:email|call|message|text|remind|schedule)\s+(.+)$"
)
_TRAILING_SCHEDULING_IN_PERSON_REGEX = re.compile(
    r"\s+(?i:today|tomorrow|tonight|this morning|this afternoon|this evening|next week|this weekend).*$"
)
_LOCATION_PREP_REGEX = re.compile(
    r"\b(?:at|in|from|to|near)\s+([A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*)*)"
)


@lru_cache(maxsize=1)
def _load_nlp() -> tuple[Language, str]:
    if spacy is None:
        return _RegexOnlyNLP(), "regex_only"

    for model_name in ("en_core_web_lg", "en_core_web_sm"):
        try:
            nlp = spacy.load(model_name)
            _install_ruler(nlp)
            return nlp, model_name
        except OSError:
            continue

    nlp = spacy.blank("en")
    _install_ruler(nlp)
    return nlp, "spacy_blank_en"


def _install_ruler(nlp: Language) -> None:
    if "entity_ruler" in nlp.pipe_names:
        return
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([*_DATE_PATTERNS, *_COMMAND_PATTERNS])


def extract_entities(txt: str) -> dict[str, Any]:
    nlp, backend = _load_nlp()
    doc = nlp(txt)

    extracted: dict[str, Any] = {
        "date": None,
        "time": None,
        "person": [],
        "location": [],
        "command": None,
        "priority": None,
        "category": None,
        "parser_backend": backend,
    }

    for ent in doc.ents:
        if ent.label_ == "DATE" and not extracted["date"]:
            extracted["date"] = ent.text
        elif ent.label_ == "TIME" and not extracted["time"]:
            extracted["time"] = ent.text
        elif ent.label_ == "PERSON":
            person = _normalize_person_entity(ent.text)
            if person and person not in extracted["person"]:
                extracted["person"].append(person)
        elif ent.label_ in _LOCATION_LABELS and ent.text not in extracted["location"]:
            extracted["location"].append(ent.text)
        elif ent.label_ == "COMMAND" and not extracted["command"]:
            extracted["command"] = ent.text

    _fill_regex_entities(txt, extracted)

    lower_txt = txt.lower()
    if any(word in lower_txt for word in ["urgent", "asap", "immediately", "emergency", "critical"]):
        extracted["priority"] = "High"
    elif any(word in lower_txt for word in ["important", "soon", "eod", "end of day"]):
        extracted["priority"] = "Medium"
    elif any(word in lower_txt for word in ["whenever", "no rush", "eventually", "low priority"]):
        extracted["priority"] = "Low"
    else:
        extracted["priority"] = "Normal"

    extracted["category"] = _classify_category(lower_txt)
    return extracted


def _fill_regex_entities(text: str, extracted: dict[str, Any]) -> None:
    if not extracted["time"]:
        match = _TIME_REGEX.search(text)
        if match:
            extracted["time"] = match.group(0)

    if not extracted["date"]:
        match = _DATE_REGEX.search(text)
        if match:
            extracted["date"] = match.group(0)

    if not extracted["person"]:
        command_match = _PERSON_COMMAND_REGEX.search(text)
        if command_match:
            extracted["person"].append(command_match.group(1).strip())

    if not extracted["person"]:
        for match in _PERSON_PREP_REGEX.finditer(text):
            candidate = match.group(1).strip()
            if candidate and candidate not in extracted["person"]:
                extracted["person"].append(candidate)

    for match in _LOCATION_PREP_REGEX.finditer(text):
        candidate = match.group(1).strip()
        if candidate and candidate not in extracted["location"]:
            extracted["location"].append(candidate)

    if not extracted["command"]:
        match = re.match(r"^\s*(email|schedule|remind|book|buy|call|message|text)\b", text, re.IGNORECASE)
        if match:
            extracted["command"] = match.group(1).lower()


def _normalize_person_entity(value: str) -> str | None:
    candidate = value.strip(" ,.;:!?")
    if not candidate:
        return None

    command_match = _LEADING_COMMAND_IN_PERSON_REGEX.match(candidate)
    if command_match:
        candidate = command_match.group(1).strip()

    candidate = _TRAILING_SCHEDULING_IN_PERSON_REGEX.sub("", candidate).strip(" ,.;:!?")

    words = candidate.split()
    if not words:
        return None

    while words and words[-1].lower() in {"about", "regarding", "re", "at", "on", "by", "before", "tomorrow", "today", "tonight"}:
        words.pop()

    if not words:
        return None

    if len(words) > 2:
        words = words[:2]

    return " ".join(words)


def _classify_category(lower_txt: str) -> str | None:
    scores = {}
    for category, keywords in _CATEGORY_RULES:
        hits = sum(1 for keyword in keywords if keyword in lower_txt)
        if hits:
            scores[category] = hits
    return max(scores, key=scores.get) if scores else None


class _RegexOnlyDoc:
    def __init__(self) -> None:
        self.ents: list[Any] = []


class _RegexOnlyNLP:
    pipe_names: list[str] = []

    def __call__(self, _: str) -> _RegexOnlyDoc:
        return _RegexOnlyDoc()
