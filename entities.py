import spacy
from preprocess import preprocess_text

nlp = spacy.load("en_core_web_lg")

ruler = nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})

patterns = [
    
    {"label": "DATE", "pattern": [{"lower": "new"}, {"lower": "year"}, {"lower": "'s"}, {"lower": "eve"}]},
    {"label": "DATE", "pattern": [{"lower": "new"}, {"lower": "years"}, {"lower": "eve"}]},
    {"label": "DATE", "pattern": [{"lower": "christmas"}]},
    {"label": "DATE", "pattern": [{"lower": "thanksgiving"}]},

    {"label": "COMMAND", "pattern": [{"lower": "email"}]},
    {"label": "COMMAND", "pattern": [{"lower": "schedule"}]},
    {"label": "COMMAND", "pattern": [{"lower": "remind"}]},
    {"label": "COMMAND", "pattern": [{"lower": "book"}]},
    {"label": "COMMAND", "pattern": [{"lower": "buy"}]}
]

ruler.add_patterns(patterns)

# CHANGE: set of location labels pulled out to avoid rebuilding a list every loop iteration
_LOCATION_LABELS = {"GPE", "LOC", "FAC", "ORG"}

def extract_entities(txt: str) -> dict:
    doc = nlp(txt)
    
    extracted = {
        "date": None,
        "time": None,
        "person": [],       # CHANGE: list instead of None — captures ALL people
        "location": [],     # CHANGE: list instead of None — captures ALL locations (ex: "at the library and the cafe" should get both)
        "command": None,    # CHANGE: added — the COMMAND ruler patterns were defined above but never read back
        "priority": None,
        "category": None,
    }

    for ent in doc.ents:
        if ent.label_ == "DATE" and not extracted["date"]:
            extracted['date'] = ent.text
        if ent.label_ == "TIME" and not extracted["time"]:
            extracted['time'] = ent.text
        # CHANGE: append instead of first-only, skip duplicates
        if ent.label_ == "PERSON":
            if ent.text not in extracted["person"]:
                extracted["person"].append(ent.text)
        # CHANGE: uses the _LOCATION_LABELS set, appends instead of first-only
        if ent.label_ in _LOCATION_LABELS:
            if ent.text not in extracted["location"]:
                extracted["location"].append(ent.text)
        # CHANGE: reads back the COMMAND label from the entity ruler
        if ent.label_ == "COMMAND" and not extracted["command"]:
            extracted["command"] = ent.text

    # CHANGE: return None instead of empty list for cleaner output
    extracted["person"] = extracted["person"] or None
    extracted["location"] = extracted["location"] or None
    
    lower_txt = txt.lower()
    
    # Check priority
    # CHANGE: added "immediately" (what preprocess expands "asap" into if shorthand map is used) and "critical". Added a Medium tier for "important", "soon", "eod", "end of day".
    if any(word in lower_txt for word in ["urgent", "asap", "immediately", "emergency", "critical"]):
        extracted["priority"] = "High"
    elif any(word in lower_txt for word in ["important", "soon", "eod", "end of day"]):
        extracted["priority"] = "Medium"
    elif any(word in lower_txt for word in ["whenever", "no rush", "eventually", "low priority"]):
        extracted["priority"] = "Low"
    else:
        extracted["priority"] = "Normal"
        
    # Check category
    # CHANGE: replaced if/elif chain with keyword scoring so the best-matching category wins rather than whichever rule comes first.
    extracted["category"] = _classify_category(lower_txt)

    return extracted

"""
CHANGE: category logic extracted into its own function with scoring.
The old if/elif chain meant "call the manager" always hit Work (manager)and never considered Communication (call). Scoring picks the category
with the most keyword hits. Also expanded with Communication, Finance, Meeting."""
_CATEGORY_RULES = [
    ("Health",        ["gym", "workout", "run", "doctor", "dentist", "prescription", "therapy", "checkup"]),
    ("Work",          ["meeting", "manager", "report", "eod", "review", "submit", "deploy", "presentation", "deadline"]),
    ("Errands",       ["buy", "store", "groceries", "shop", "pick up", "drop off", "return"]),
    ("Communication", ["email", "call", "message", "text", "send", "reply", "contact"]),
    ("Meeting",       ["dinner", "lunch", "standup", "sync", "1-on-1"]),
    ("Finance",       ["tax", "invoice", "payment", "budget", "accounting", "bill"]),
]

def _classify_category(lower_txt: str) -> str | None:
    scores = {}
    for category, keywords in _CATEGORY_RULES:
        hits = sum(1 for kw in keywords if kw in lower_txt)
        if hits:
            scores[category] = hits
    return max(scores, key=scores.get) if scores else None


if __name__ == "__main__":
    edge_case_tasks = [
        # 1. Punctuation & Numeric Traps
        "Remind me to call the architect at 2:30 PM sharp.",
        "Buy 1.5kg of coffee beans from the store.",
        "Email the team about the v2.0 update before E.O.D.",
        # 2. Stopword/Connector Traps
        "Meet at the library in 10 minutes.",
        "Fly from London to New York tomorrow.",
        "Remind me to go to the gym.",
        # 3. Slang, Typos & Contractions
        "I'll finish the report tmrw morning.",
        "Gotta pick up Sarah's prescription by 6pm.",
        "Don't forget to msg the group abt the venue.",
        # 4. Case Sensitivity & Ambiguity
        "Email Mark about the mark on the carpet.",
        "Buy an Apple watch at the Apple store.",
        "Remind May to pay the bill in May.",
        # 5. Multi-word Entities
        "Book a table at The Golden Lion for New Year's Eve.",
        "Pick up the high-speed HDMI cable from Best Buy.",
        "Schedule a 1-on-1 with the Manager.",
    ]

    for t in edge_case_tasks:
        clean_text = preprocess_text(t)
        print(extract_entities(clean_text))