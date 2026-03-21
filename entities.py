
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

def extract_entities(txt: str) -> dict:
    doc = nlp(txt)
    
    extracted = {
        "date": None,
        "time": None,
        "person": None,
        "location": None,
        "priority": None,
        "category": None,
    }

    for ent in doc.ents:
        if ent.label_ == "DATE" and not extracted["date"]:
            extracted['date'] = ent.text
        if ent.label_ == "TIME" and not extracted["time"]:
            extracted['time'] = ent.text
        if ent.label_ == "PERSON" and not extracted["person"]:
            extracted['person'] = ent.text
        if ent.label_ in ["GPE", "LOC", "FAC", "ORG"] and not extracted["location"]:
            extracted['location'] = ent.text
    
    lower_txt = txt.lower()
    
    # Check priority
    if any(word in lower_txt for word in ["urgent", "asap", "sharp", "emergency"]):
        extracted["priority"] = "High"
    elif "whenever" in lower_txt:
        extracted["priority"] = "Low"
    else:
        extracted["priority"] = "Normal"
        
    # Check category 
    if any(word in lower_txt for word in ["gym", "workout", "run"]):
        extracted["category"] = "Health"
    elif any(word in lower_txt for word in ["meeting", "manager", "report", "eod"]):
        extracted["category"] = "Work"
    elif any(word in lower_txt for word in ["buy", "store", "groceries", "shop"]):
        extracted["category"] = "Errands"

    return extracted


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
