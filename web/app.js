const $ = (selector) => document.querySelector(selector);
const recipientsInput = $("#recipient-input");
let recipients = [];
let polling;

function toast(text) { const box = $("#toast"); box.textContent = text; box.classList.add("visible"); setTimeout(() => box.classList.remove("visible"), 2600); }
function parseRecipients(value) { return value.split(/[\s,;]+/).map((item) => item.trim()).filter(Boolean); }
function renderRecipients() {
  const parsed = parseRecipients(recipientsInput.value);
  recipients = [...new Set(parsed)];
  const chips = $("#recipient-chips");
  chips.innerHTML = recipients.map((email, index) => `<span class="chip">${email}<button type="button" data-index="${index}" aria-label="Удалить ${email}">×</button></span>`).join("");
  chips.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    recipients.splice(Number(button.dataset.index), 1); recipientsInput.value = recipients.join("\n"); renderRecipients();
  }));
  const count = recipients.length;
  $("#recipient-count").textContent = count; $("#sidebar-count").textContent = count; $("#send-count").textContent = count;
}
function preview() { $("#preview-subject").textContent = $("#subject").value.trim() || "Без темы"; $("#preview-message").textContent = $("#message").value.replaceAll("{{name}}", "Алексей"); $("#character-count").textContent = `${$("#message").value.length} символов`; }
async function api(path, options = {}) { const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options}); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Ошибка сервера"); return data; }
function showStatus(data) {
  const state = {idle:"Готово к запуску",running:"Рассылка выполняется",stopped:"Рассылка остановлена",completed:"Рассылка завершена",error:"Ошибка рассылки"}[data.state] || data.state;
  $("#status-label").textContent = state; $("#status-progress").textContent = `${data.sent + data.failed} / ${data.total}`;
  $("#progress-bar").style.width = `${data.total ? ((data.sent + data.failed) / data.total) * 100 : 0}%`;
  $("#mail-log").textContent = data.logs.length ? data.logs.map((line) => `[${line.at}] ${line.message}`).join("\n") : "Событий пока нет.";
  const running = data.state === "running"; $("#stop-button").disabled = !running; $(".send-button[type=submit]").disabled = running;
  if (!running && polling) { clearInterval(polling); polling = undefined; }
}
async function refreshStatus() { try { showStatus(await api("/api/mailing/status")); } catch (_) {} }
async function login(event) {
  event.preventDefault(); $("#login-error").textContent = "";
  try { await api("/api/login", {method:"POST", body:JSON.stringify({password: $("#login-password").value})}); $("#login-modal").classList.add("hidden"); const settings = await api("/api/settings");
    $("#sender").innerHTML = settings.senders.map((sender) => `<option>${sender}</option>`).join(""); $("#sender").value = settings.default_sender || settings.senders[0]; $("#delay").value = settings.default_delay; $("#active-from").value = settings.active_from; $("#active-to").value = settings.active_to; refreshStatus();
  } catch (error) { $("#login-error").textContent = error.message; }
}
$("#login-form").addEventListener("submit", login);
document.querySelectorAll("[data-variable]").forEach((button) => button.addEventListener("click", () => {
  const field = $("#message"); field.setRangeText(button.dataset.variable, field.selectionStart, field.selectionEnd, "end"); field.focus(); preview();
}));
document.querySelectorAll("[data-wrap]").forEach((button) => button.addEventListener("click", () => {
  const field = $("#message"), marker = button.dataset.wrap, selected = field.value.slice(field.selectionStart, field.selectionEnd) || "текст";
  field.setRangeText(`${marker}${selected}${marker}`, field.selectionStart, field.selectionEnd, "end"); field.focus(); preview();
}));
recipientsInput.addEventListener("input", renderRecipients); $("#subject").addEventListener("input", preview); $("#message").addEventListener("input", preview);
$("#import-button").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", async (event) => { const file = event.target.files[0]; if (!file) return; const imported = await file.text(); recipientsInput.value = `${recipientsInput.value}\n${imported}`.trim(); renderRecipients(); toast("Адреса импортированы"); });
$("#preview-button").addEventListener("click", () => { preview(); $(".preview-panel").scrollIntoView({behavior:"smooth"}); });
$("#save-draft").addEventListener("click", () => toast("Черновик остаётся в текущем окне браузера"));
$("#rewrite-button").addEventListener("click", () => toast("AI-рерайт применяется при отправке, если включён параметр"));
$("#mail-form").addEventListener("submit", async (event) => { event.preventDefault(); renderRecipients(); try { const status = await api("/api/mailing/start", {method:"POST", body:JSON.stringify({recipients: recipientsInput.value, subject: $("#subject").value, template: $("#message").value, sender: $("#sender").value, delay: $("#delay").value, active_from: $("#active-from").value, active_to: $("#active-to").value, rewrite: $("#rewrite").checked})}); showStatus(status); polling = setInterval(refreshStatus, 900); } catch (error) { toast(error.message); } });
$("#stop-button").addEventListener("click", async () => { try { showStatus(await api("/api/mailing/stop", {method:"POST"})); } catch (error) { toast(error.message); } });
renderRecipients(); preview();
