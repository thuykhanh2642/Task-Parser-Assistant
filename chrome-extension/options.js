const DEFAULT_API_URL = "http://127.0.0.1:8000";

const apiUrlInput = document.getElementById("apiUrl");
const saveButton = document.getElementById("saveButton");
const statusMessage = document.getElementById("statusMessage");

async function loadSettings() {
  const { apiUrl } = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL });
  apiUrlInput.value = apiUrl;
}

async function saveSettings() {
  const apiUrl = apiUrlInput.value.trim() || DEFAULT_API_URL;
  await chrome.storage.sync.set({ apiUrl });
  statusMessage.textContent = "Settings saved.";
}

saveButton.addEventListener("click", saveSettings);
document.addEventListener("DOMContentLoaded", loadSettings);
