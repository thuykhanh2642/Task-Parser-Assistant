"""
task_extractor.py: Strips extracted entities from the sentence to isolate
the core task description.
"""
import re # for regex-based cleanup

def extract_task(text: str, entities: dict | None = None) -> str | None:
    if not text:
        return None

    task_text = text

    if entities:
        removable_fields = ["date", "time", "location"]
        for field in removable_fields:
            value = entities.get(field)
            if value and isinstance(value, str):
                # Remove the entity AND a leading preposition if one is glued to it.
                # example: "at 3pm" / "by Friday" / "in Conference Room B"
                #only strips the prep that introduced this entity.
                prep_pattern = (
                    r"\b(?:at|by|on|before|in|from|near|to)\s+" + re.escape(value)
                )
                task_text = re.sub(prep_pattern, "", task_text, flags=re.IGNORECASE)
                # remove the bare value if it appeared without a preposition
                task_text = re.sub(
                    r"\b" + re.escape(value) + r"\b", "", task_text,
                    flags=re.IGNORECASE
                )

    # Clean up leftover punctuation artifacts (dangling commas, dashes, colons)
    task_text = re.sub(r"\s*[,;:—–-]\s*$", "", task_text)   # trailing
    task_text = re.sub(r"^\s*[,;:—–-]\s*", "", task_text)   # leading
    task_text = re.sub(r"\s*[,;:—–-]\s*[,;:—–-]\s*", " ", task_text)  # doubled

    # Normalize spaces
    task_text = re.sub(r"\s+", " ", task_text).strip()

    return task_text if task_text else None