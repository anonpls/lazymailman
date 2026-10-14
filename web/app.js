const $ = (selector) => document.querySelector(selector);
const recipientsInput = $("#recipient-input");
let recipients = [];
let polling;
let importedTable = null;
let mappings = [];

function toast(text) { const box = $("#toast"); box.textContent = text; box.classList.add("visible"); setTimeout(() => box.classList.remove("visible"), 2600); }
function parseRecipients(value) { return value.split(/[\s,;]+/).map((item) => item.trim()).filter(Boolean); }
function logText(logs) { return logs.length ? logs.map((line) => `[${line.at}] ${line.message}`).join("\n") : "Событий пока нет."; }
function renderRecipients() {
  const parsed = parseRecipients(recipientsInput.value); recipients = [...new Set(parsed)];
  const chips = $("#recipient-chips"); chips.innerHTML = recipients.map((email, index) => `<span class="chip">${email}<button type="button" data-index="${index}" aria-label="Удалить ${email}">×</button></span>`).join("");
  chips.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => { recipients.splice(Number(button.dataset.index), 1); recipientsInput.value = recipients.join("\n"); renderRecipients(); }));
  $("#recipient-count").textContent = recipients.length; $("#sidebar-count").textContent = recipients.length; $("#send-count").textContent = recipients.length;
}
function personalized(text, cells) {
  const values = {email: cells?.[0] || recipients[0] || "alex@example.com"};
  mappings.forEach(m => {const value = cells?.[m.index]; values[m.name] = !value || ["null","none","nan","n/a","na","0","undefined","-"].includes(String(value).trim().toLowerCase()) ? m.default : value;});
  return text.replace(/{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}/g, (match, key) => Object.hasOwn(values,key) ? values[key] : match);
}
function preview() { $("#preview-subject").textContent = personalized($("#subject").value.trim() || "Без темы", importedTable?.rows[0]); $("#preview-message").textContent = personalized($("#message").value, importedTable?.rows[0]); $("#character-count").textContent = `${$("#message").value.length} символов`; }
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
function showStatus(data) {
  const state = {idle:"Готово к запуску",running:"Рассылка выполняется",stopped:"Рассылка остановлена",completed:"Рассылка завершена",error:"Ошибка рассылки"}[data.state] || data.state;
  $("#status-label").textContent = state; $("#status-progress").textContent = `${data.sent + data.failed} / ${data.total}`; $("#progress-bar").style.width = `${data.total ? ((data.sent + data.failed) / data.total) * 100 : 0}%`;
  $("#mail-log").textContent = logText(data.logs);
  const running = data.state === "running"; $("#stop-button").disabled = !running; $(".send-button[type=submit]").disabled = running;
  if (!running && polling) { clearInterval(polling); polling = undefined; }
}
async function refreshStatus() { try { showStatus(await api("/api/mailing/status")); } catch (_) {} }
function showPage() { const page = location.pathname.split("/").filter(Boolean)[0] || "compose"; document.querySelectorAll("[data-view]").forEach((view) => view.classList.toggle("active", view.dataset.view === page)); document.querySelectorAll("[data-page]").forEach((item) => item.classList.toggle("active", item.dataset.page === page)); document.title = `${document.querySelector(`[data-view="${page}"] h1`)?.textContent || "Рассылка"}`; }
async function loadAuthenticatedPage() {
  const settings = await api("/api/settings");
  $("#sender").innerHTML = settings.senders.map((sender) => `<option>${sender}</option>`).join(""); $("#sender").value = settings.default_sender || settings.senders[0]; $("#delay").value = settings.default_delay; $("#active-from").value = settings.active_from; $("#active-to").value = settings.active_to; refreshStatus();
}
function renderVariableButtons() {
  const host = $("#variable-buttons"); host.replaceChildren();
  for (const name of ["email", ...mappings.map(m=>m.name).filter(Boolean)]) {
    const button=document.createElement("button"); button.type="button"; button.textContent=`{{${name}}}`;
    button.addEventListener("click",()=>{const field=$("#message");field.setRangeText(button.textContent,field.selectionStart,field.selectionEnd,"end");field.focus();preview();});host.append(button);
  }
}
function renderMappings() {
  const host=$("#variable-mappings");host.replaceChildren();
  importedTable.headers.slice(1).forEach((header,i)=>{
    const mapping=mappings[i];const row=document.createElement("div");row.className="mapping-row";
    const label=document.createElement("label");label.textContent=header;
    const name=document.createElement("input");name.placeholder="variable_name";name.value=mapping.name;name.setAttribute("aria-label",`Переменная для ${header}`);
    const fallback=document.createElement("input");fallback.placeholder="Значение по умолчанию";fallback.value=mapping.default;fallback.setAttribute("aria-label",`По умолчанию для ${header}`);
    name.addEventListener("input",()=>{mapping.name=name.value.trim();renderVariableButtons();preview();});
    fallback.addEventListener("input",()=>{mapping.default=fallback.value;preview();});
    row.append(label,name,fallback);host.append(row);
  });renderVariableButtons();
}
function showImportedTable(data) {
  importedTable=data;mappings=data.headers.slice(1).map((header,i)=>({index:i+1,name:header.toLowerCase().replace(/[^a-z0-9_]+/g,"_").replace(/^([^a-z_])/,'_$1'),default:""}));
  const table=$("#import-preview");table.replaceChildren();
  const head=document.createElement("tr");data.headers.forEach(h=>{const cell=document.createElement("th");cell.textContent=h;head.append(cell);});table.append(head);
  data.rows.slice(0,100).forEach(row=>{const tr=document.createElement("tr");row.forEach(value=>{const td=document.createElement("td");td.textContent=value;tr.append(td);});table.append(tr);});
  $("#table-summary").textContent=`${data.rows.length} строк, ${data.headers.length} столбцов. Показаны первые 100 строк.`;
  $("#table-import").hidden=false;
  recipientsInput.value=data.rows.map(r=>r[0]).join("\n");renderRecipients();renderMappings();preview();
}
document.querySelectorAll("[data-wrap]").forEach((button) => button.addEventListener("click", () => { const field = $("#message"), marker = button.dataset.wrap, selected = field.value.slice(field.selectionStart, field.selectionEnd) || "текст"; field.setRangeText(`${marker}${selected}${marker}`, field.selectionStart, field.selectionEnd, "end"); field.focus(); preview(); }));
recipientsInput.addEventListener("input", renderRecipients); $("#subject").addEventListener("input", preview); $("#message").addEventListener("input", preview); $("#refresh-preview").addEventListener("click", preview); $("#refresh-logs")?.addEventListener("click", refreshStatus);
$("#import-button").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", async (event) => {
  const file=event.target.files[0];if(!file)return;
  try {
    if(file.name.toLowerCase().endsWith(".txt")) {importedTable=null;mappings=[];$("#table-import").hidden=true;renderVariableButtons();recipientsInput.value=await file.text();renderRecipients();toast("Адреса импортированы");return;}
    const form=new FormData();form.append("file",file);
    const response=await fetch("/api/import-table",{method:"POST",body:form,credentials:"same-origin"});
    if(response.status===401){location.href="/login";return;}
    const data=await response.json();if(!response.ok)throw new Error(data.error||"Ошибка импорта");
    showImportedTable(data);toast("Таблица импортирована");
  } catch(error){toast(error.message);console.error(error);}
  finally {event.target.value="";}
});
$("#preview-button").addEventListener("click", () => { preview(); $(".preview-panel").scrollIntoView({behavior:"smooth"}); }); $("#save-draft").addEventListener("click", () => toast("Черновик остаётся в текущем окне браузера")); $("#rewrite-button").addEventListener("click", () => toast("AI-рерайт применяется при отправке, если включён параметр"));
$("#mail-form").addEventListener("submit", async (event) => { event.preventDefault(); renderRecipients(); try { const status = await api("/api/mailing/start", {method:"POST", body:JSON.stringify({recipients: recipientsInput.value, subject: $("#subject").value, template: $("#message").value, sender: $("#sender").value, delay: $("#delay").value, active_from: $("#active-from").value, active_to: $("#active-to").value, rewrite: $("#rewrite").checked, table_rows: importedTable?.rows, variable_columns: mappings.filter(m=>m.name)})}); showStatus(status); polling = setInterval(refreshStatus, 900); } catch (error) { toast(error.message); } });
$("#stop-button").addEventListener("click", async () => { try { showStatus(await api("/api/mailing/stop", {method:"POST"})); } catch (error) { toast(error.message); } });
showPage(); renderRecipients(); renderVariableButtons(); preview();
loadAuthenticatedPage().catch((error) => {
  console.error("Не удалось загрузить настройки:", error);
  toast(`Не удалось загрузить настройки: ${error.message}`);
});
