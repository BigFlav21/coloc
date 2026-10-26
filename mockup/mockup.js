// Maquette statique : seulement de la navigation et des interactions factices.
const views = ["login", "pin", "home", "menus", "courses", "idees"];

function show(name) {
  if (!views.includes(name)) name = "home";
  views.forEach(v => document.getElementById("v-" + v).classList.toggle("active", v === name));
  document.querySelectorAll("nav.tabs a").forEach(a => a.classList.toggle("active", a.dataset.v === name));
  document.getElementById("fab").style.display = (name === "home") ? "" : "none";
  document.body.classList.toggle("bare", name === "login" || name === "pin");
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", () => show(location.hash.slice(1)));
show(location.hash.slice(1));

document.addEventListener("click", e => {
  const w = e.target.closest(".who-btn");
  if (w) { document.querySelectorAll(".who-btn").forEach(b => b.classList.remove("sel")); w.classList.add("sel"); }
});

// Cases à cocher (tâches, courses)
document.addEventListener("click", e => {
  const c = e.target.closest(".check");
  if (c) {
    c.classList.toggle("on");
    c.textContent = c.classList.contains("on") ? "✓" : "";
    const label = c.parentElement.querySelector(".label");
    if (label) label.classList.toggle("done-text", c.classList.contains("on"));
  }
  const v = e.target.closest(".vote");
  if (v) {
    const n = v.querySelector("b");
    const on = v.classList.toggle("on");
    n.textContent = +n.textContent + (on ? 1 : -1);
  }
  const r = e.target.closest("[data-rsvp]");
  if (r) {
    const group = r.parentElement;
    group.querySelectorAll("[data-rsvp]").forEach(b => b.classList.remove("on"));
    r.classList.add("on");
  }
  const t = e.target.closest(".type-pick button");
  if (t) {
    t.parentElement.querySelectorAll("button").forEach(b => b.classList.remove("sel"));
    t.classList.add("sel");
  }
  if (e.target.closest("[data-open]")) document.getElementById("modal").classList.add("open");
  if (e.target.closest("[data-close]") || e.target.id === "modal") document.getElementById("modal").classList.remove("open");
});

// Calendrier d'octobre 2026 (factice)
const events = { 27: "dinner", 29: "party", 30: "guest", 31: "party", 3: "away", 5: "dinner" };
const grid = document.getElementById("cal");
["L", "M", "M", "J", "V", "S", "D"].forEach(d => grid.insertAdjacentHTML("beforeend", `<div class="cal-dow">${d}</div>`));
// 1er octobre 2026 = jeudi → 3 cases vides (lun, mar, mer) = fin septembre
const cells = [];
for (let d = 28; d <= 30; d++) cells.push({ n: d, off: true });
for (let d = 1; d <= 31; d++) cells.push({ n: d, month: 10 });
for (let d = 1; d <= 8; d++) cells.push({ n: d, off: true, next: true });
cells.slice(0, 35).forEach(c => {
  const ev = !c.off || c.next ? events[c.n] : null;
  const dot = ev && (c.month === 10 || c.next) ? `<div class="dot ${ev}"></div>` : "";
  const today = c.month === 10 && c.n === 26 ? " today" : "";
  grid.insertAdjacentHTML("beforeend", `<div class="cal-day${c.off ? " off" : ""}${today}"><span class="n">${c.n}</span>${c.month === 10 ? dot : ""}</div>`);
});
