chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "schedule-reminder") {
    return false;
  }

  scheduleReminder(message.reminder)
    .then(() => sendResponse({ ok: true }))
    .catch((error) => sendResponse({ ok: false, error: error.message }));

  return true;
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (!alarm.name.startsWith("task_")) {
    return;
  }

  const { reminders = {} } = await chrome.storage.local.get({ reminders: {} });
  const reminder = reminders[alarm.name];
  if (!reminder) {
    return;
  }

  await chrome.notifications.create(alarm.name, {
    type: "basic",
    iconUrl: chrome.runtime.getURL("icon-128.png"),
    title: "Task Reminder",
    message: reminder.task || reminder.rawText || "You have a scheduled task."
  });
});

async function scheduleReminder(reminder) {
  if (!reminder?.id || !reminder?.reminderAt) {
    throw new Error("Reminder payload is incomplete.");
  }

  const triggerAt = new Date(reminder.reminderAt).getTime();
  if (!Number.isFinite(triggerAt) || triggerAt <= Date.now()) {
    throw new Error("Reminder time must be in the future.");
  }

  const { reminders = {} } = await chrome.storage.local.get({ reminders: {} });
  reminders[reminder.id] = reminder;

  await chrome.storage.local.set({ reminders });
  await chrome.alarms.create(reminder.id, { when: triggerAt });
}
