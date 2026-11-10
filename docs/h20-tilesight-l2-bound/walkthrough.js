"use strict";
const sliders = ["m", "n", "k"].map(x => document.getElementById(`tile-${x}`));
function updateTile() {
  const [m,n,k] = sliders.map(x => Number(x.value));
  [m,n,k].forEach((v,i) => { document.getElementById(`${["m","n","k"][i]}-value`).textContent = v; });
  document.getElementById("a-row").setAttribute("y", 12 + m*24);
  document.getElementById("b-column").setAttribute("x", 20 + n*10);
  document.getElementById("selected-tile").setAttribute("x", 20 + n*10);
  document.getElementById("selected-tile").setAttribute("y", 12 + m*24);
  document.getElementById("c-range").textContent = `C[${m*16}:${(m+1)*16}, ${n*128}:${(n+1)*128}]`;
  document.getElementById("a-range").textContent = `A[${m*16}:${(m+1)*16}, ${k*64}:${(k+1)*64}] — shared across 78 output columns`;
  document.getElementById("b-range").textContent = `B[${k*64}:${(k+1)*64}, ${n*128}:${(n+1)*128}] — shared across 4 output rows`;
}
sliders.forEach(x => x.addEventListener("input", updateTile));
updateTile();
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  const last = button.dataset.view === "last";
  document.getElementById("schedule-first").hidden = last;
  document.getElementById("schedule-last").hidden = !last;
  document.querySelectorAll("[data-view]").forEach(other => other.setAttribute("aria-pressed",String(other===button)));
}));
