from __future__ import annotations

import re

try:
    import contractions
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-light environments
    contractions = None

try:
    from spellchecker import SpellChecker
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-light environments
    SpellChecker = None  # type: ignore[assignment]

try:
    from spacy.lang.en import English
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-light environments
    English = None  # type: ignore[assignment]

from utils import SHORTHAND_MAP, WAKE_WORDS

_TOKENIZER = English().tokenizer if English else None
_SPELLCHECKER = SpellChecker() if SpellChecker else None
_WAKE_WORD_PATTERN = re.compile("|".join(WAKE_WORDS), re.IGNORECASE)
_PROTECTED = {
    "eod",
    "hdmi",
    "gmail",
    "uber",
    "lyft",
    "venmo",
    "wifi",
    "covid",
    "ai",
    "api",
    "url",
    "pdf",
    "ios",
    "sql",
    "slack",
    "figma",
}


def preprocess_text(txt: str) -> str:
    if contractions:
        txt = contractions.fix(txt)
    txt = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", txt)
    txt = _WAKE_WORD_PATTERN.sub("", txt)

    clean_tokens: list[str] = []
    for token in _tokenize(txt):
        word = token.text
        word_lower = word.lower()

        if word_lower in SHORTHAND_MAP:
            replacement = SHORTHAND_MAP[word_lower]
            word = replacement.capitalize() if word.istitle() else replacement
        elif (
            token.is_alpha
            and word.islower()
            and len(word) > 2
            and word_lower not in _PROTECTED
            and _SPELLCHECKER is not None
            and _SPELLCHECKER.unknown([word])
        ):
            correction = _SPELLCHECKER.correction(word)
            if correction:
                word = correction

        clean_tokens.append(word + token.whitespace_)

    clean_text = "".join(clean_tokens)
    return re.sub(r"\s+", " ", clean_text).strip()


def _tokenize(text: str) -> list[object]:
    if _TOKENIZER is not None:
        return list(_TOKENIZER(text))

    wrapped = []
    for match in re.finditer(r"\w+|[^\w\s]", text, re.UNICODE):
        end = match.end()
        whitespace_match = re.match(r"\s*", text[end:])
        whitespace = whitespace_match.group(0) if whitespace_match else ""
        wrapped.append(_SimpleToken(match.group(0), whitespace))
    return wrapped


class _SimpleToken:
    def __init__(self, text: str, whitespace: str) -> None:
        self.text = text
        self.whitespace_ = whitespace
        self.is_alpha = text.isalpha()
