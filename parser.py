from __future__ import annotations

from entities import extract_entities
from preprocess import preprocess_text
from schemas import ParseResponse
from task_extractor import extract_task


def parse_task(text: str) -> ParseResponse:
    cleaned_text = preprocess_text(text)
    entities = extract_entities(cleaned_text)
    task = extract_task(cleaned_text, entities)
    warnings, ambiguities = _analyze_parse(cleaned_text, task, entities)
    confidence = _estimate_confidence(cleaned_text, task, entities, warnings, ambiguities)

    return ParseResponse(
        raw_text=text,
        cleaned_text=cleaned_text,
        task=task,
        date=entities.get("date"),
        time=entities.get("time"),
        person=entities.get("person") or [],
        location=entities.get("location") or [],
        command=entities.get("command"),
        priority=entities.get("priority") or "Normal",
        category=entities.get("category"),
        parser_backend=entities.get("parser_backend", "unknown"),
        confidence=confidence,
        warnings=warnings,
        ambiguities=ambiguities,
    )


def _analyze_parse(
    cleaned_text: str,
    task: str | None,
    entities: dict,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    ambiguities: list[str] = []

    if entities.get("parser_backend") == "regex_only":
        warnings.append("Running in regex-only mode; named entity extraction may be limited.")

    if not task:
        warnings.append("Unable to isolate a clear task description.")
    elif len(task) < max(4, len(cleaned_text) // 5):
        warnings.append("Task text was reduced significantly during cleanup.")

    if not entities.get("command"):
        warnings.append("No explicit action verb was identified.")

    if len(entities.get("person") or []) > 1:
        ambiguities.append("Multiple people were detected; the primary assignee or recipient may be unclear.")

    if len(entities.get("location") or []) > 1:
        ambiguities.append("Multiple locations were detected; the destination may be ambiguous.")

    if entities.get("date") and not entities.get("time"):
        ambiguities.append("A date was found without a specific time.")

    if entities.get("time") and not entities.get("date"):
        ambiguities.append("A time was found without a specific date.")

    if not entities.get("category"):
        ambiguities.append("No strong category match was found.")

    return warnings, ambiguities


def _estimate_confidence(
    cleaned_text: str,
    task: str | None,
    entities: dict,
    warnings: list[str],
    ambiguities: list[str],
) -> float:
    score = 0.35

    if task:
        score += 0.2
        reduction_ratio = len(task) / max(len(cleaned_text), 1)
        if 0.35 <= reduction_ratio <= 0.95:
            score += 0.1
    if entities.get("command"):
        score += 0.15
    if entities.get("date"):
        score += 0.05
    if entities.get("time"):
        score += 0.05
    if entities.get("person"):
        score += 0.05
    if entities.get("location"):
        score += 0.05
    if entities.get("category"):
        score += 0.05
    if entities.get("parser_backend") not in {"regex_only", "spacy_blank_en"}:
        score += 0.05

    score -= min(0.2, len(warnings) * 0.05)
    score -= min(0.15, len(ambiguities) * 0.03)

    return round(max(0.0, min(1.0, score)), 2)
