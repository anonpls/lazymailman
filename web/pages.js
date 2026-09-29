const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {credentials: "same-origin", headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json();
  if (response.status === 401) {
    const next = `${location.pathname}${location.search}`;
    location.href = `/login?next=${encodeURIComponent(next)}`;
    throw new Error(data.error || "Требуется вход.");
  }
  if (!response.ok) throw new Error(data.error || "Ошибка сервера");
  return data;
}

function formatLogs(logs) {
  return logs.length ? logs.map((line) => `[${line.at}] ${line.message}`).join("\n") : "Событий пока нет.";
}

async function refreshLogs() {
  const output = $("#full-mail-log");
  if (!output) return;
  try { output.textContent = formatLogs((await api("/api/mailing/status")).logs); }
  catch (error) { output.textContent = error.message; }
}

$("#refresh-logs")?.addEventListener("click", refreshLogs);
refreshLogs();
