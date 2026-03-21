from spellchecker import SpellChecker
from spacy.lang.en import English
from utils import SHORTHAND_MAP, WAKE_WORDS
import re
import contractions


def preprocess_text(txt: str) -> str:
    txt = contractions.fix(txt) # type: ignore
    txt = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', txt)
    txt = re.sub("|".join(WAKE_WORDS), "", txt, flags=re.IGNORECASE) # Renive wake words
    
    # Tokenization
    nlp = English()
    tokenizer = nlp.tokenizer
    tokens = tokenizer(txt)
    sc = SpellChecker()

    clean_tokens = []

    for token in tokens:
        word = token.text
        word_lower = word.lower()

        if word_lower in SHORTHAND_MAP: # Map to full length word
            if word.istitle():
                word = SHORTHAND_MAP[word_lower].capitalize()
            else:
                word = SHORTHAND_MAP[word_lower]

        elif word.isupper() and len(word) > 1: # Skip Acronyms
            pass

        elif token.is_alpha: # Fixes misspelled words
            if sc.unknown([word]):
                correction = sc.correction(word)
                if correction is not None:
                    word = correction

        clean_tokens.append(word + token.whitespace_)

    clean_text = "".join(clean_tokens)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip() # Remove extra whitespace

    return clean_text


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
        print("-" * 20)
        print(f"{t} -----> {preprocess_text(t)}")
