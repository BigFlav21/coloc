// Seul JS applicatif : modale d'ajout d'évènement. Le reste passe par HTMX.
document.addEventListener("click", e => {
  const modal = document.getElementById("modal");
  if (!modal) return;
  if (e.target.closest("[data-open]")) modal.classList.add("open");
  if (e.target.closest("[data-close]") || e.target === modal) modal.classList.remove("open");
  const t = e.target.closest(".type-pick button");
  if (t) {
    t.parentElement.querySelectorAll("button").forEach(b => b.classList.remove("sel"));
    t.classList.add("sel");
    document.getElementById("ev-type").value = t.dataset.type;
  }
});
