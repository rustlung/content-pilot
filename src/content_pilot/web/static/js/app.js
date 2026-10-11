document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-ai-form]").forEach((form) => form.addEventListener("submit", () => {
    const button = form.querySelector("button[type='submit']");
    if (button) { button.disabled = true; button.textContent = button.dataset.loadingText || "Генерация…"; }
  }));
  document.querySelectorAll("form[data-confirm]").forEach((form) => form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));
  document.querySelectorAll("[data-copy-target]").forEach((button) => button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target) return;
    await navigator.clipboard.writeText(target.textContent || "");
    const original = button.textContent; button.textContent = "Скопировано";
    setTimeout(() => { button.textContent = original; }, 1600);
  }));
});
