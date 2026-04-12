const DEFAULT_API_URL = "http://127.0.0.1:8000";

const taskInput = document.getElementById("taskInput");
const apiUrlInput = document.getElementById("apiUrl");
const resultOutput = document.getElementById("resultOutput");
const statusMessage = document.getElementById("statusMessage");
const summaryCards = document.getElementById("summaryCards");
const feedbackSection = document.getElementById("feedbackSection");
const confidenceBadge = document.getElementById("confidenceBadge");
const reminderSummary = document.getElementById("reminderSummary");
const parseButton = document.getElementById("parseButton");
const saveButton = document.getElementById("saveButton");
const scheduleButton = document.getElementById("scheduleButton");

let latestParsedResult = null;
let latestReminderAt = null;

async function loadSettings() {
  const { apiUrl } = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL });
  apiUrlInput.value = apiUrl;
}

async function saveSettings() {
  const apiUrl = apiUrlInput.value.trim() || DEFAULT_API_URL;
  await chrome.storage.sync.set({ apiUrl });
  statusMessage.textContent = "Backend URL saved.";
}

async function parseTask() {
  const text = taskInput.value.trim();
  const apiUrl = apiUrlInput.value.trim() || DEFAULT_API_URL;

  if (!text) {
    statusMessage.textContent = "Enter a task first.";
    return;
  }

  statusMessage.textContent = "Parsing task...";
  resultOutput.textContent = "Waiting for response...";
  summaryCards.innerHTML = "";
  feedbackSection.innerHTML = "";
  confidenceBadge.textContent = "Parsing";
  confidenceBadge.className = "badge badge-muted";
  reminderSummary.textContent = "Resolving reminder time...";
  scheduleButton.disabled = true;
  latestParsedResult = null;
  latestReminderAt = null;

  try {
    const response = await fetch(`${apiUrl}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(errorBody || `Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const reminderAt = resolveReminderTimestamp(data.date, data.time);
    latestParsedResult = data;
    latestReminderAt = reminderAt;
    renderResult(data);
    if (reminderAt) {
      reminderSummary.textContent = `Reminder will be scheduled for ${formatDateTime(reminderAt)}.`;
      scheduleButton.disabled = false;
      statusMessage.textContent = "Task parsed successfully. Reminder is ready to schedule.";
    } else {
      reminderSummary.textContent = "Parsed successfully, but I could not turn the date/time into a concrete reminder timestamp.";
      statusMessage.textContent = "Task parsed successfully, but the reminder time needs a clearer date or time.";
    }
  } catch (error) {
    resultOutput.textContent = "Unable to reach the parser service.";
    statusMessage.textContent = error.message;
    confidenceBadge.textContent = "Unavailable";
    confidenceBadge.className = "badge badge-low";
    reminderSummary.textContent = "Reminder unavailable.";
  }
}

function renderResult(data) {
  resultOutput.textContent = JSON.stringify(data, null, 2);

  const cards = [
    ["Task", data.task || "Not identified"],
    ["Command", data.command || "Not identified"],
    ["Date", data.date || "None"],
    ["Time", data.time || "None"],
    ["People", (data.person || []).join(", ") || "None"],
    ["Location", (data.location || []).join(", ") || "None"],
    ["Priority", data.priority || "Normal"],
    ["Category", data.category || "Uncategorized"]
  ];

  summaryCards.innerHTML = cards.map(([label, value]) => `
    <article class="card">
      <span class="card-label">${escapeHtml(label)}</span>
      <div class="card-value">${escapeHtml(value)}</div>
    </article>
  `).join("");

  const sections = [];
  if ((data.warnings || []).length) {
    sections.push(renderFeedbackBlock("Warnings", data.warnings));
  }
  if ((data.ambiguities || []).length) {
    sections.push(renderFeedbackBlock("Ambiguities", data.ambiguities));
  }
  feedbackSection.innerHTML = sections.join("");

  const confidence = Number(data.confidence || 0);
  confidenceBadge.textContent = `${Math.round(confidence * 100)}% confidence`;
  confidenceBadge.className = `badge ${confidenceClass(confidence)}`;
}

async function scheduleReminder() {
  if (!latestParsedResult || !latestReminderAt) {
    statusMessage.textContent = "Parse a task with a valid date and time first.";
    return;
  }

  const reminder = {
    id: `task_${Date.now()}`,
    rawText: latestParsedResult.raw_text,
    task: latestParsedResult.task || latestParsedResult.raw_text,
    date: latestParsedResult.date,
    time: latestParsedResult.time,
    reminderAt: latestReminderAt.toISOString(),
    parseResult: latestParsedResult
  };

  try {
    const response = await chrome.runtime.sendMessage({
      type: "schedule-reminder",
      reminder
    });

    if (!response?.ok) {
      throw new Error(response?.error || "Failed to schedule reminder.");
    }

    reminderSummary.textContent = `Reminder scheduled for ${formatDateTime(new Date(reminder.reminderAt))}.`;
    statusMessage.textContent = "Reminder scheduled locally in Chrome.";
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

function renderFeedbackBlock(title, items) {
  return `
    <section class="feedback-block">
      <h3>${escapeHtml(title)}</h3>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </section>
  `;
}

function confidenceClass(value) {
  if (value >= 0.75) {
    return "badge-high";
  }
  if (value >= 0.5) {
    return "badge-medium";
  }
  return "badge-low";
}

function resolveReminderTimestamp(dateText, timeText) {
  if (!dateText || !timeText) {
    return null;
  }

  const now = new Date();
  const baseDate = resolveDate(dateText, now);
  const timeParts = resolveTime(timeText);

  if (!baseDate || !timeParts) {
    return null;
  }

  const reminderAt = new Date(baseDate);
  reminderAt.setHours(timeParts.hours, timeParts.minutes, 0, 0);

  if (reminderAt <= now) {
    return null;
  }

  return reminderAt;
}

function resolveDate(value, now) {
  const normalized = String(value).trim().toLowerCase();
  const date = new Date(now);
  date.setHours(0, 0, 0, 0);

  if (normalized === "today") {
    return date;
  }
  if (normalized === "tomorrow") {
    date.setDate(date.getDate() + 1);
    return date;
  }
  if (normalized === "tonight") {
    return date;
  }
  if (normalized === "weekend" || normalized === "this weekend") {
    return nextWeekday(date, 6);
  }
  if (normalized === "next week") {
    date.setDate(date.getDate() + 7);
    return date;
  }

  const weekdayMap = {
    sunday: 0,
    monday: 1,
    tuesday: 2,
    wednesday: 3,
    thursday: 4,
    friday: 5,
    saturday: 6
  };

  if (weekdayMap[normalized] !== undefined) {
    return nextWeekday(date, weekdayMap[normalized]);
  }

  return null;
}

function resolveTime(value) {
  const normalized = String(value).trim().toLowerCase();

  if (normalized === "noon") {
    return { hours: 12, minutes: 0 };
  }
  if (normalized === "midnight") {
    return { hours: 0, minutes: 0 };
  }
  if (normalized === "tonight") {
    return { hours: 20, minutes: 0 };
  }

  const match = normalized.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
  if (!match) {
    return null;
  }

  let hours = Number(match[1]);
  const minutes = Number(match[2] || 0);
  const meridiem = match[3];

  if (meridiem === "am" && hours === 12) {
    hours = 0;
  } else if (meridiem === "pm" && hours !== 12) {
    hours += 12;
  }

  return { hours, minutes };
}

function nextWeekday(baseDate, targetWeekday) {
  const date = new Date(baseDate);
  const delta = (targetWeekday - date.getDay() + 7) % 7 || 7;
  date.setDate(date.getDate() + delta);
  return date;
}

function formatDateTime(date) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

parseButton.addEventListener("click", parseTask);
saveButton.addEventListener("click", saveSettings);
scheduleButton.addEventListener("click", scheduleReminder);
document.addEventListener("DOMContentLoaded", loadSettings);
