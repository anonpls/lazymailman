const form = document.querySelector("#login-form");
const password = document.querySelector("#login-password");
const errorBox = document.querySelector("#login-error");

function safeNext() {
  const value = new URLSearchParams(location.search).get("next");
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({password: password.value}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ошибка входа");
    location.replace(safeNext());
  } catch (error) {
    errorBox.textContent = error.message;
    password.select();
  }
});
