SHORTHAND_MAP = {
    # Days & Time
    "tmrw": "tomorrow",
    "tmw": "tomorrow",
    "mon": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "wed": "Wednesday",
    "thurs": "Thursday",
    "fri": "Friday",
    "wknd": "weekend",
    "min": "minute",
    "mins": "minutes",
    "hr": "hour",
    "hrs": "hours",
    "sec": "second",
    "secs": "seconds",

    # Task Actions & Objects
    "msg": "message",
    "mtg": "meeting",
    "appt": "appointment",
    "prep": "prepare",
    "doc": "document",
    "docs": "documents",
    "info": "information",
    "calc": "calculate",
    "chk": "check",

    # Connectors & Misc
    "abt": "about",
    "b4": "before",
    "w/": "with",
    "w/o": "without",
#NOTE: got rid of asap, could be misinterpreted as a task description rather than a time entity, or maybe used as priority
}


WAKE_WORDS = (
    r"^remind me to\s+",
    r"^please\s+",
    r"^can you\s+",
    r"^i need to\s+",
)