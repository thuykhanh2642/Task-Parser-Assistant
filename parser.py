#parser.py: preprocess -> extract entities > extract task.
from preprocess import preprocess_text
from entities import extract_entities
from task_extractor import extract_task


def parse_task(text: str) -> dict:
    #clean text
    cleaned_text = preprocess_text(text)

    #extract entities
    entities = extract_entities(cleaned_text)

    #extract core task description (strip entities from sentence)
    task = extract_task(cleaned_text, entities)

    #assemble structured result
    return {
        "raw_text":     text,
        "cleaned_text": cleaned_text,
        "task":         task,
        "date":         entities.get("date"),
        "time":         entities.get("time"),
        "person":       entities.get("person"),
        "location":     entities.get("location"),
        "priority":     entities.get("priority"),
        "category":     entities.get("category"),
    }