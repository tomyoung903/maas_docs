"use strict";
const sliders = Object.fromEntries(["m", "n", "k"].map(key => [key, document.getElementById(`tile-${key}`)]));
function updateTile() {
  const m = Number(sliders.m.value), n = Number(sliders.n.value), k = Number(sliders.k.value);
  for (const [key, value] of Object.entries({m, n, k})) document.getElementById(`${key}-value`).textContent = value;
  const tile = document.getElementById("selected-tile");
  tile.setAttribute("x", 16 + 8*n); tile.setAttribute("y", 16 + 8*m);
  document.getElementById("c-range").textContent = `C[${m*128}:${(m+1)*128}, ${n*128}:${(n+1)*128}]`;
  document.getElementById("a-range").textContent = `A[${m*128}:${(m+1)*128}, ${k*64}:${(k+1)*64}]`;
  document.getElementById("b-range").textContent = `B[${k*64}:${(k+1)*64}, ${n*128}:${(n+1)*128}]`;
}
Object.values(sliders).forEach(slider => slider.addEventListener("input", updateTile));
updateTile();
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  const last = button.dataset.view === "last";
  document.getElementById("schedule-first").hidden = last;
  document.getElementById("schedule-last").hidden = !last;
  document.querySelectorAll("[data-view]").forEach(other => other.setAttribute("aria-pressed", String(other === button)));
}));

// The exported visual keeps its own sandbox and CSP. Resize its trusted outer
// wrapper without entering the sandboxed visualization document.
const reuseFrame = document.getElementById("l2-reuse-frame");
if (reuseFrame) {
  let reuseResizeObserver;
  const fitReuseFrame = () => {
    const body = reuseFrame.contentDocument?.body;
    if (!body) return;
    const height = Math.ceil(body.getBoundingClientRect().height);
    if (height > 100 && height < 5000 && reuseFrame.style.height !== `${height}px`) {
      reuseFrame.style.height = `${height}px`;
    }
  };
  reuseFrame.addEventListener("load", () => {
    reuseResizeObserver?.disconnect();
    const body = reuseFrame.contentDocument?.body;
    if (body) {
      reuseResizeObserver = new ResizeObserver(fitReuseFrame);
      reuseResizeObserver.observe(body);
      fitReuseFrame();
    }
  });
}
