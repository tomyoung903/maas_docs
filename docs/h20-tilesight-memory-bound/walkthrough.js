"use strict";
const nSlider = document.getElementById("tile-n");
const kSlider = document.getElementById("tile-k");
function updateTile() {
  const n = Number(nSlider.value), k = Number(kSlider.value);
  document.getElementById("n-value").textContent = n;
  document.getElementById("k-value").textContent = k;
  document.getElementById("selected-tile").setAttribute("x", 18+n);
  document.getElementById("c-range").textContent = `C[0:16, ${n*128}:${(n+1)*128}]`;
  document.getElementById("a-range").textContent = `A[0:16, ${k*64}:${(k+1)*64}] — same across output tiles`;
  document.getElementById("b-range").textContent = `B[${k*64}:${(k+1)*64}, ${n*128}:${(n+1)*128}]`;
}
[nSlider,kSlider].forEach(s => s.addEventListener("input", updateTile));
updateTile();
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  const last = button.dataset.view === "last";
  document.getElementById("schedule-first").hidden = last;
  document.getElementById("schedule-last").hidden = !last;
  document.querySelectorAll("[data-view]").forEach(other => other.setAttribute("aria-pressed", String(other === button)));
}));
