(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('ledger-data').textContent);
  const ops = Object.fromEntries(data.ops.map(op => [op.key, op]));
  const select = document.getElementById('layer');
  const hide = document.getElementById('hide-inactive');
  const details = [...document.querySelectorAll('#tree details')];
  const amount = n => {
    if (!n) return '0 FLOP';
    for (const [scale, unit] of [[1e15, 'PFLOP'], [1e12, 'TFLOP'], [1e9, 'GFLOP']]) {
      if (Math.abs(n) >= scale) return `${(n / scale).toLocaleString('en-US', {minimumFractionDigits: 6, maximumFractionDigits: 6})} ${unit}`;
    }
    return `${n.toLocaleString('en-US')} FLOP`;
  };
  function count(op) {
    return select.value === 'all' ? op.hy_count : Number(op.hy_layers.includes(Number(select.value)));
  }
  function update() {
    document.querySelectorAll('.tree-cost').forEach(el => {
      const keys = el.dataset.keys.split(',');
      const value = keys.reduce((s, key) => s + count(ops[key]) * ops[key].hy, 0);
      el.textContent = amount(value);
      const active = keys.some(key => count(ops[key]) > 0);
      const row = el.closest('details');
      row.hidden = hide.checked && !active;
      row.classList.toggle('inactive', !active);
    });
    document.querySelectorAll('.op-count').forEach(el => {
      const n = count(ops[el.dataset.op]);
      el.textContent = `${n} logical instance${n === 1 ? '' : 's'}`;
    });
    const total = data.ops.reduce((s, op) => s + count(op) * op.hy, 0);
    document.getElementById('scope-total').textContent = amount(total);
    document.getElementById('scope-label').textContent = select.value === 'all'
      ? 'Whole-model 100K prefill' : `Layer ${select.value}: 100K prefill, whole parallel group`;
  }
  select.addEventListener('change', update);
  hide.addEventListener('change', update);
  function setDepth(depth) {
    details.forEach(el => { el.open = depth === 'all' || (el.classList.contains('group') && Number(el.dataset.depth) <= Number(depth)); });
    document.querySelectorAll('button[data-depth]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.depth === depth)));
  }
  document.querySelectorAll('button[data-depth]').forEach(el => el.addEventListener('click', () => setDepth(el.dataset.depth)));
  document.querySelectorAll('[data-select-layer]').forEach(el => el.addEventListener('click', () => {
    select.value = el.dataset.selectLayer;
    update();
  }));
  const svg = document.getElementById('layer-chart');
  const ns = 'http://www.w3.org/2000/svg';
  const max = Math.ceil(Math.max(...data.layers.flatMap(l => [l.hy, l.glm])) / 1e13) * 1e13;
  function element(tag, attrs, text) {
    const e = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    if (text !== undefined) e.textContent = text;
    return e;
  }
  for (let i = 0; i <= 4; i++) {
    const y = 200 - i * 44;
    svg.append(element('line', {x1: 56, x2: 1025, y1: y, y2: y, stroke: '#dde4e5'}));
    svg.append(element('text', {x: 46, y: y + 4, 'text-anchor': 'end', fill: '#58656c', 'font-size': 11}, (max * i / 4 / 1e12).toFixed(0)));
  }
  svg.append(element('text', {x: 6, y: 14, fill: '#58656c', 'font-size': 11}, 'TFLOP'));
  data.layers.forEach((row, i) => {
    const x = 60 + i * 12.3;
    for (const [m, offset, fill] of [['glm', 0, '#7e8994'], ['hy', 5, '#087f76']]) {
      const height = row[m] / max * 176;
      const bar = element('rect', {x: x + offset, y: 200 - height, width: 4, height, fill});
      bar.append(element('title', {}, `Layer ${i}, ${m === 'hy' ? 'HY4' : 'GLM-5.2'}: ${amount(row[m])}`));
      svg.append(bar);
    }
    if (i % 10 === 0 || i === 77) svg.append(element('text', {x: x + 3, y: 221, fill: '#58656c', 'font-size': 11, 'text-anchor': 'middle'}, String(i)));
  });
  svg.append(element('text', {x: 990, y: 238, fill: '#58656c', 'font-size': 11}, 'Layer'));
  const sections = [...document.querySelectorAll('main>section')];
  let scrollQueued = false;
  function markSection() {
    const active = sections.filter(s => s.getBoundingClientRect().top <= 200).at(-1) || sections[0];
    document.querySelectorAll('aside nav a').forEach(a => a.classList.toggle('current', a.hash === `#${active.id}`));
    scrollQueued = false;
  }
  addEventListener('scroll', () => {
    if (!scrollQueued) { scrollQueued = true; requestAnimationFrame(markSection); }
  }, {passive: true});
  setDepth('2');
  update();
  markSection();
})();
