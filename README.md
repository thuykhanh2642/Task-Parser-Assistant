# Task Parser Assistant

Task Parser Assistant is a lightweight Python service that turns natural-language tasks into structured JSON. This repo now includes:

- a CLI for local testing
- a FastAPI backend for production-style integration
- a Manifest V3 Chrome extension popup frontend
- automated tests for the parser flow

## Backend

### 1. Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

The app prefers `en_core_web_lg`, falls back to `en_core_web_sm`, and finally to a regex-assisted blank English pipeline if no spaCy model is installed.

### 2. Run the API

```powershell
uvicorn api:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 3. API endpoints

- `GET /health`
- `POST /parse`

Example request:

```json
{
  "text": "Email Sarah about the launch plan tomorrow at 3pm"
}
```

## Chrome Extension

The extension lives in `chrome-extension/`.

### Load it in Chrome

1. Open `chrome://extensions`
2. Enable Developer mode
3. Click Load unpacked
4. Select the `chrome-extension` folder

The popup lets you:

- paste a task
- send the task to the local API and view structured results
- convert parsed date/time into a local reminder timestamp
- save reminders in Chrome storage
- schedule `chrome.alarms`
- show Chrome notifications when alarms fire

### Reminder MVP behavior

For phrases like `Email Sarah about the launch plan tomorrow at 3pm`, the flow is:

1. The popup sends the text to the backend.
2. The backend returns parsed `date` and `time`.
3. The extension resolves those into a concrete browser-local timestamp.
4. The extension stores the reminder in `chrome.storage.local`.
5. The extension creates a `chrome.alarms` entry like `task_<timestamp>`.
6. When the alarm fires, the background service worker shows a Chrome notification.

The popup uses the local API at `http://127.0.0.1:8000` and also supports fuzzy reminder phrases when resolving local timestamps, including `later today`, `later tonight`, `this afternoon`, `this evening`, and `soon`.

## Tests

```powershell
pytest
```
