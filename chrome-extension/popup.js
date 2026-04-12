const DEFAULT_API_URL = "http://127.0.0.1:8000";

const taskInput = document.getElementById("taskInput");
const apiUrlInput = document.getElementById("apiUrl");
const resultOutput = document.getElementById("resultOutput");
const statusMessage = document.getElementById("statusMessage");
const summaryCards = document.getElementById("summaryCards");
const feedbackSection = document.getElementById("feedbackSection");
const confidenceBadge = document.getElementById("confidenceBadge");
const parseButton = document.getElementById("parseButton");
const saveButton = document.getElementById("saveButton");

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
    renderResult(data);
    statusMessage.textContent = "Task parsed successfully.";
  } catch (error) {
    resultOutput.textContent = "Unable to reach the parser service.";
    statusMessage.textContent = error.message;
    confidenceBadge.textContent = "Unavailable";
    confidenceBadge.className = "badge badge-low";
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
document.addEventListener("DOMContentLoaded", loadSettings);
