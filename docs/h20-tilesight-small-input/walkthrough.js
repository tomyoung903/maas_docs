'use strict';
const ns = document.getElementById('tile-n');
const ks = document.getElementById('tile-k');
function updateTile() {
  const n=Number(ns.value), k=Number(ks.value);
  document.getElementById('n-value').textContent=n;
  document.getElementById('k-value').textContent=k;
  document.getElementById('selected-tile').setAttribute('x',18+3*n);
  document.getElementById('c-range').textContent=`C[0:16, ${n*128}:${(n+1)*128}]`;
  document.getElementById('a-range').textContent=`A[0:16, ${k*64}:${(k+1)*64}] — reused across output tiles`;
  document.getElementById('b-range').textContent=`B[${k*64}:${(k+1)*64}, ${n*128}:${(n+1)*128}]`;
}
[ns,ks].forEach(s=>s.addEventListener('input',updateTile));
updateTile();
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{
  const last=b.dataset.view==='last';
  document.getElementById('schedule-first').hidden=last;
  document.getElementById('schedule-last').hidden=!last;
  document.querySelectorAll('[data-view]').forEach(other=>other.setAttribute('aria-pressed',String(other===b)));
}));
