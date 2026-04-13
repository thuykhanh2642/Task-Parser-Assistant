const DEFAULT_API_URL = "http://127.0.0.1:8000";

const taskInput = document.getElementById("taskInput");
const resultOutput = document.getElementById("resultOutput");
const statusMessage = document.getElementById("statusMessage");
const summaryCards = document.getElementById("summaryCards");
const feedbackSection = document.getElementById("feedbackSection");
const confidenceBadge = document.getElementById("confidenceBadge");
const reminderSummary = document.getElementById("reminderSummary");
const parseButton = document.getElementById("parseButton");
const scheduleButton = document.getElementById("scheduleButton");

let latestParsedResult = null;
let latestReminderAt = null;

async function parseTask() {
  const text = taskInput.value.trim();

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
    const response = await fetch(`${DEFAULT_API_URL}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(errorBody || `Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const reminderAt = resolveReminderTimestamp(data);
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
    ["Time", data.time || inferTimeText(data) || "None"],
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
    time: latestParsedResult.time || inferTimeText(latestParsedResult),
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

function resolveReminderTimestamp(parseResult) {
  const dateText = parseResult?.date;
  const timeText = parseResult?.time || inferTimeText(parseResult);
  if (!dateText || !timeText) {
    return null;
  }

  const now = new Date();
  const baseDate = resolveDate(dateText, now);
  const timeParts = resolveTime(timeText, baseDate, now);

  if (!baseDate || !timeParts) {
    return null;
  }

  const reminderAt = new Date(baseDate);
  reminderAt.setHours(timeParts.hours, timeParts.minutes, 0, 0);

  if (reminderAt <= now) {
    if (isSameLocalDay(baseDate, now)) {
      return bumpFutureReminder(reminderAt, now);
    }
    return null;
  }

  return reminderAt;
}

function inferTimeText(parseResult) {
  const haystacks = [
    parseResult?.raw_text,
    parseResult?.cleaned_text,
    parseResult?.task
  ].filter(Boolean);

  for (const value of haystacks) {
    const normalized = String(value).toLowerCase();
    if (normalized.includes("later today")) {
      return "later today";
    }
    if (normalized.includes("later tonight")) {
      return "later tonight";
    }
    if (normalized.includes("this morning")) {
      return "this morning";
    }
    if (normalized.includes("this afternoon")) {
      return "this afternoon";
    }
    if (normalized.includes("this evening")) {
      return "this evening";
    }
    if (normalized.includes("soon")) {
      return "soon";
    }
  }

  return null;
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

function resolveTime(value, baseDate, now) {
  const normalized = String(value).trim().toLowerCase();
  const fuzzyTime = resolveFuzzyTime(normalized, baseDate, now);
  if (fuzzyTime) {
    return fuzzyTime;
  }

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

function resolveFuzzyTime(value, baseDate, now) {
  if (!baseDate) {
    return null;
  }

  const sameDay = isSameLocalDay(baseDate, now);

  if (value === "later today") {
    return toTimeParts(sameDay ? addHoursRounded(now, 2) : setTime(baseDate, 17, 0));
  }
  if (value === "later tonight") {
    return { hours: 20, minutes: 0 };
  }
  if (value === "this morning") {
    return { hours: 9, minutes: 0 };
  }
  if (value === "this afternoon") {
    return { hours: 15, minutes: 0 };
  }
  if (value === "this evening") {
    return { hours: 18, minutes: 0 };
  }
  if (value === "soon") {
    return toTimeParts(addMinutesRounded(now, 30));
  }

  return null;
}

function addHoursRounded(date, hoursToAdd) {
  const next = new Date(date);
  next.setMinutes(0, 0, 0);
  next.setHours(next.getHours() + hoursToAdd);
  return next;
}

function addMinutesRounded(date, minutesToAdd) {
  const next = new Date(date.getTime() + minutesToAdd * 60 * 1000);
  next.setSeconds(0, 0);
  return next;
}

function setTime(date, hours, minutes) {
  const next = new Date(date);
  next.setHours(hours, minutes, 0, 0);
  return next;
}

function toTimeParts(date) {
  return { hours: date.getHours(), minutes: date.getMinutes() };
}

function isSameLocalDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function bumpFutureReminder(reminderAt, now) {
  const bumped = new Date(reminderAt);
  if (bumped <= now) {
    bumped.setTime(addMinutesRounded(now, 15).getTime());
  }
  return bumped;
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
scheduleButton.addEventListener("click", scheduleReminder);
