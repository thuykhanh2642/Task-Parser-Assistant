from fastapi.testclient import TestClient
import pytest

from api import app
from parser import parse_task
from preprocess import preprocess_text


def test_preprocess_expands_shorthand() -> None:
    assert preprocess_text("Please msg Sam tmrw") == "message Sam tomorrow"


def test_parse_task_returns_structured_response() -> None:
    result = parse_task("Email Sarah tomorrow at 3pm about the demo")

    assert result.command == "email"
    assert result.date == "tomorrow"
    assert result.time and result.time.lower().replace(" ", "") == "3pm"
    assert "Sarah" in result.person
    assert result.task == "Email Sarah about the demo"
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.warnings, list)
    assert isinstance(result.ambiguities, list)


def test_api_parse_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/parse", json={"text": "Buy groceries this weekend"})

    assert response.status_code == 200
    body = response.json()
    assert body["raw_text"] == "Buy groceries this weekend"
    assert body["date"].lower() == "weekend"
    assert body["command"] == "buy"
    assert "confidence" in body
    assert "warnings" in body
    assert "ambiguities" in body


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("Call Mom tonight", {"task": "Call Mom tonight", "command": "call", "date": "tonight"}),
        ("Buy groceries this weekend", {"task": "Buy groceries this weekend", "command": "buy", "date": "weekend"}),
        ("Schedule 1-on-1 with Alex on Friday", {"task": "Schedule 1-on-1 with Alex", "command": "schedule", "date": "Friday"}),
        ("Book dentist appointment at noon tomorrow", {"task": "Book dentist appointment", "command": "book", "time": "noon"}),
        ("Email Sarah about the launch plan tomorrow at 3pm", {"task": "Email Sarah about the launch plan", "person": "Sarah"}),
        ("Submit the expense report by Monday", {"task": "Submit the expense report", "date": "Monday"}),
        ("Pick up the HDMI cable from Best Buy", {"task": "Pick up the HDMI cable from Best Buy", "location": "Best Buy"}),
        ("Text Jordan when you get home", {"task": "Text Jordan when you get home", "command": "text"}),
        ("Pay the electricity bill today", {"task": "Pay the electricity bill today", "date": "today"}),
        ("Meet Priya at Central Library at 6pm", {"task": "Meet Priya at Central Library", "time": "6 pm"}),
        ("Review the API spec before Thursday", {"task": "Review the API spec", "date": "Thursday"}),
        ("Send invoice to Acme next week", {"task": "Send invoice to Acme next week", "date": "next week"}),
        ("Message Sam about dinner tonight", {"task": "Message Sam about dinner tonight", "date": "tonight"}),
        ("Remind me to call the architect at 2:30 PM sharp.", {"task": "call the architect sharp.", "time": "2:30 PM"}),
        ("Remind me to do homework for cs374 today", {"task": "do homework for cs374", "date": "today", "command": "remind", "category": "School"}),
        ("Remind me to call Sam later today", {"task": "call Sam later today", "date": "today", "time": "later today"}),
    ],
)
def test_representative_phrases(phrase: str, expected: dict[str, str]) -> None:
    result = parse_task(phrase)

    for field, expected_value in expected.items():
        actual = getattr(result, field)
        if isinstance(actual, list):
            assert expected_value in actual
        else:
            assert actual == expected_value


def test_spacy_person_command_prefix_is_removed() -> None:
    result = parse_task("Email Sarah about the launch plan tomorrow at 3pm")

    assert result.person == ["Sarah"]
    assert result.task == "Email Sarah about the launch plan"


def test_reminder_intent_survives_wake_word_preprocessing() -> None:
    result = parse_task("Remind me to do homework for cs374 today")

    assert result.task == "do homework for cs374"
    assert result.date == "today"
    assert result.command == "remind"
    assert result.category == "School"


def test_relative_minute_time_is_extracted_without_date_ambiguity() -> None:
    result = parse_task("go to class in 1 min")

    assert result.task == "go to class"
    assert result.time == "in 1 minute"
    assert result.date is None
    assert "A time was found without a specific date." not in result.ambiguities


def test_relative_hour_time_is_extracted_from_reminder_phrase() -> None:
    result = parse_task("Remind me to submit the report in 2 hours")

    assert result.task == "submit the report"
    assert result.time == "in 2 hours"
    assert result.command == "remind"
