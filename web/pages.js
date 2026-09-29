const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {credentials: "same-origin", headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json();
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

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault(); $("#login-error").textContent = "";
  try {
    await api("/api/login", {method: "POST", body: JSON.stringify({password: $("#login-password").value})});
    $("#login-modal").classList.add("hidden");
    refreshLogs();
  } catch (error) { $("#login-error").textContent = error.message; }
});
$("#refresh-logs")?.addEventListener("click", refreshLogs);

async function initializeAuth() {
  const modal = $("#login-modal");
  modal.classList.add("hidden");
  try {
    const status = await api("/api/mailing/status");
    const output = $("#full-mail-log");
    if (output) output.textContent = formatLogs(status.logs);
  } catch (error) { $("#login-error").textContent = error.message; modal.classList.remove("hidden"); }
}

initializeAuth();
