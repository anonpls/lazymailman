const recipients = ["alex@example.com", "maria@studio.ru", "hello@north.co", "team@orbit.io"];
const input = document.querySelector("#recipient-input");
const chips = document.querySelector("#recipient-chips");
const count = document.querySelector("#recipient-count");
const sidebarCount = document.querySelector("#sidebar-count");
const sendCount = document.querySelector("#send-count");
const subject = document.querySelector("#subject");
const message = document.querySelector("#message");
const previewSubject = document.querySelector("#preview-subject");
const previewMessage = document.querySelector("#preview-message");
const charCount = document.querySelector("#character-count");
const toast = document.querySelector("#toast");

function showToast(text) {
  toast.textContent = text;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 2600);
}

function renderRecipients() {
  chips.innerHTML = "";
  recipients.forEach((email, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `${email}<button type="button" aria-label="Удалить ${email}">×</button>`;
    chip.querySelector("button").addEventListener("click", () => {
      recipients.splice(index, 1);
      renderRecipients();
    });
    chips.append(chip);
  });
  const label = `${recipients.length}`;
  count.textContent = label;
  sidebarCount.textContent = label;
  sendCount.textContent = label;
}

function updatePreview() {
  previewSubject.textContent = subject.value.trim() || "Без темы";
  previewMessage.textContent = message.value.replaceAll("{{name}}", "Алексей");
  charCount.textContent = `${message.value.length} символов`;
}

function addRecipient(value) {
  const email = value.trim().replace(/[;,]+$/, "");
  if (!email) return;
  if (!email.includes("@") || !email.includes(".")) {
    showToast("Введите корректный email-адрес");
    return;
  }
  if (recipients.includes(email)) {
    showToast("Этот получатель уже добавлен");
    return;
  }
  recipients.push(email);
  input.value = "";
  renderRecipients();
}

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === ",") {
    event.preventDefault();
    addRecipient(input.value);
  }
});
input.addEventListener("blur", () => addRecipient(input.value));
subject.addEventListener("input", updatePreview);
message.addEventListener("input", updatePreview);

document.querySelectorAll("[data-variable]").forEach((button) => {
  button.addEventListener("click", () => {
    const cursor = message.selectionStart;
    message.setRangeText(button.dataset.variable, cursor, message.selectionEnd, "end");
    message.focus();
    updatePreview();
  });
});

document.querySelectorAll("[data-wrap]").forEach((button) => {
  button.addEventListener("click", () => {
    const marker = button.dataset.wrap;
    const start = message.selectionStart;
    const selected = message.value.slice(start, message.selectionEnd) || "текст";
    message.setRangeText(`${marker}${selected}${marker}`, start, message.selectionEnd, "end");
    message.focus();
    updatePreview();
  });
});

document.querySelectorAll(".delivery-option").forEach((option) => {
  option.addEventListener("click", () => {
    document.querySelectorAll(".delivery-option").forEach((item) => item.classList.remove("selected"));
    option.classList.add("selected");
  });
});

document.querySelector("#import-button").addEventListener("click", () => document.querySelector("#file-input").click());
document.querySelector("#file-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  const imported = text.split(/[\s,;]+/).filter((item) => item.includes("@"));
  imported.forEach((email) => { if (!recipients.includes(email)) recipients.push(email); });
  renderRecipients();
  showToast(`Импортировано адресов: ${imported.length}`);
  event.target.value = "";
});

document.querySelector("#refresh-preview").addEventListener("click", () => { updatePreview(); showToast("Предпросмотр обновлён"); });
document.querySelector("#preview-button").addEventListener("click", () => { updatePreview(); document.querySelector(".preview-panel").scrollIntoView({ behavior: "smooth", block: "start" }); });
document.querySelector("#save-draft").addEventListener("click", () => showToast("Черновик сохранён"));
document.querySelector("#rewrite-button").addEventListener("click", () => showToast("AI-переформулировка будет доступна после подключения OpenRouter"));
document.querySelector("#mail-form").addEventListener("submit", (event) => { event.preventDefault(); showToast(`Рассылка для ${recipients.length} получателей готова к запуску`); });

renderRecipients();
updatePreview();
