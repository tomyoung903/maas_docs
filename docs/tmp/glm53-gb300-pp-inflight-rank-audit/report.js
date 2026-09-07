(() => {
  'use strict';
  const data = window.AUDIT;
  const colors = ['#226db1', '#0c8277', '#a57000', '#aa3f72'];
  const dash = [[], [7, 3], [2, 3], [10, 3, 2, 3]];
  const states = {strict: '#147d75', tied: '#b9c9ce', below: '#c74d49', zero: '#edf0f1'};
  const tooltip = document.querySelector('#tooltip');
  const charts = [];
  const formatTime = t => new Date((t + 28800) * 1000).toISOString().slice(11, 19);
  const fmtShort = t => formatTime(t).slice(0, 5);
  const mean = data.summary.mean_per_pod_by_rank_nonzero;
  const classify = vals => {
    const top = Math.max(...vals);
    return !top ? 'zero' : vals[0] < top ? 'below' : vals.filter(x => x === top).length === 1 ? 'strict' : 'tied';
  };
  const stateText = {strict:'PP0 strictly highest', tied:'PP0 tied for highest', below:'Another rank exceeds PP0', zero:'All inflight counts are zero'};
  document.querySelector('#mean-bars').innerHTML = mean.map((value, rank) => `<div class="mean-row"><span style="color:${colors[rank]}">PP${rank}</span><div class="mean-track"><i style="background:${colors[rank]};width:${100 * value / 2.6}%"></i></div><b>${value.toFixed(2)}</b></div>`).join('');
  document.querySelector('#rank-legend').innerHTML = colors.map((c, i) => `<span><i class="line" style="border-color:${c};border-top-style:${i === 0 ? 'solid' : i === 2 ? 'dotted' : 'dashed'}"></i>PP${i}</span>`).join('') + '<span style="color:#56646c">Y: requests in rank-local inflight queue</span>';
  for (const pod of data.pods) {
    const option = document.createElement('option'); option.value = pod.suffix; option.textContent = pod.suffix;
    document.querySelector('#pod').append(option);
  }
  const start = data.time[0], end = data.time.at(-1);
  let range = [start, end];

  function niceMax(value) {
    const step = value <= 8 ? 2 : value <= 20 ? 5 : 10;
    return Math.max(4, Math.ceil((value + 1) / step) * step);
  }

  function draw(chart, hoverIndex = null) {
    const {canvas, pod, bounds, yMax, marker} = chart;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    const ctx = canvas.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
    const left = 36, right = w - 12, top = 10, bottom = h - 49;
    const x = t => left + (t - bounds[0]) / (bounds[1] - bounds[0]) * (right - left);
    const y = v => bottom - v / yMax * (bottom - top);
    chart.geometry = {left, right, top, bottom};
    ctx.font = '11px system-ui'; ctx.lineWidth = 1; ctx.setLineDash([]);
    for (let v = 0; v <= yMax; v += yMax / 4) {
      ctx.strokeStyle = '#e3e8ea'; ctx.beginPath(); ctx.moveTo(left, y(v)); ctx.lineTo(right, y(v)); ctx.stroke();
      ctx.fillStyle = '#56646c'; ctx.textAlign = 'right'; ctx.fillText(Number.isInteger(v) ? v : v.toFixed(1), left - 7, y(v) + 4);
    }
    const lo = Math.max(0, Math.floor((bounds[0] - start) / 15));
    const hi = Math.min(data.time.length - 1, Math.ceil((bounds[1] - start) / 15));
    ctx.save(); ctx.beginPath(); ctx.rect(left, top, right - left, bottom - top + 1); ctx.clip();
    // Draw exact sampled values without vertical jitter. Dash patterns distinguish tied curves.
    for (let r = 0; r < 4; r++) {
      ctx.strokeStyle = colors[r]; ctx.lineWidth = r === 0 ? 2 : 1.5; ctx.setLineDash(dash[r]); ctx.beginPath();
      for (let i = lo; i <= hi; i++) {
        if (i === lo) ctx.moveTo(x(data.time[i]), y(pod.ranks[r][i]));
        else { ctx.lineTo(x(data.time[i]), y(pod.ranks[r][i - 1])); ctx.lineTo(x(data.time[i]), y(pod.ranks[r][i])); }
      }
      ctx.stroke();
    }
    ctx.restore(); ctx.setLineDash([]);
    for (let i = lo; i < hi; i++) {
      const a = Math.max(left, x(data.time[i])), b = Math.min(right, x(data.time[i + 1]));
      if (b <= a) continue;
      ctx.fillStyle = states[classify(pod.ranks.map(vals => vals[i]))];
      ctx.fillRect(a, bottom + 9, b - a + 0.1, 7);
    }
    const targetStep = (bounds[1] - bounds[0]) / (w < 600 ? 4 : 8);
    const tickStep = [15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200].find(s => s >= targetStep) || 14400;
    for (let t = Math.ceil(bounds[0] / tickStep) * tickStep; t <= bounds[1]; t += tickStep) {
      ctx.fillStyle = '#56646c'; ctx.textAlign = x(t) - left < 30 ? 'left' : right - x(t) < 30 ? 'right' : 'center';
      ctx.fillText(bounds[1] - bounds[0] < 600 ? formatTime(t) : fmtShort(t), x(t), h - 12);
    }
    const selected = hoverIndex ?? (marker != null ? data.time.indexOf(marker) : -1);
    if (selected >= 0 && data.time[selected] >= bounds[0] && data.time[selected] <= bounds[1]) {
      const at = x(data.time[selected]);
      ctx.strokeStyle = '#34434b'; ctx.lineWidth = 1; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(at, top); ctx.lineTo(at, bottom + 17); ctx.stroke(); ctx.setLineDash([]);
      for (let r = 0; r < 4; r++) {
        ctx.fillStyle = colors[r]; ctx.beginPath(); ctx.arc(at, y(pod.ranks[r][selected]), 3.3, 0, 2 * Math.PI); ctx.fill();
      }
    }
  }

  function wire(chart) {
    chart.canvas.addEventListener('mousemove', e => {
      const rect = chart.canvas.getBoundingClientRect(), gx = chart.geometry;
      const fraction = Math.max(0, Math.min(1, (e.clientX - rect.left - gx.left) / (gx.right - gx.left)));
      const t = chart.bounds[0] + fraction * (chart.bounds[1] - chart.bounds[0]);
      const i = Math.max(0, Math.min(data.time.length - 1, Math.round((t - start) / 15)));
      const vals = chart.pod.ranks.map(v => v[i]);
      draw(chart, i);
      tooltip.innerHTML = `<strong>${chart.pod.suffix} &middot; ${formatTime(data.time[i])} Beijing</strong>` + vals.map((v, r) => `<div class="tip-row"><span style="color:${colors[r]}">PP${r}</span><b>${v}</b></div>`).join('') + `<div class="tip-state">${stateText[classify(vals)]}</div>`;
      tooltip.hidden = false;
      tooltip.style.left = Math.max(8, Math.min(e.clientX + 16, innerWidth - tooltip.offsetWidth - 12)) + 'px';
      tooltip.style.top = Math.max(8, Math.min(e.clientY + 16, innerHeight - tooltip.offsetHeight - 12)) + 'px';
    });
    chart.canvas.addEventListener('mouseleave', () => { tooltip.hidden = true; draw(chart); });
  }

  function rebuild() {
    tooltip.hidden = true;
    const selected = document.querySelector('#pod').value;
    const visible = data.pods.filter(p => selected === 'all' || p.suffix === selected);
    const zoom = +document.querySelector('#zoom').value;
    const pan = document.querySelector('#pan'); pan.disabled = zoom === 1;
    const span = (range[1] - range[0]) / zoom;
    const offset = (range[1] - range[0] - span) * (+pan.value / 1000);
    const bounds = [range[0] + offset, range[0] + offset + span];
    const lo = Math.max(0, Math.floor((bounds[0] - start) / 15)), hi = Math.min(data.time.length, Math.ceil((bounds[1] - start) / 15) + 1);
    let maximum = 0;
    for (const pod of data.pods) for (const vals of pod.ranks) for (let i = lo; i < hi; i++) maximum = Math.max(maximum, vals[i]);
    const yMax = niceMax(maximum);
    document.querySelector('#window-label').textContent = `${formatTime(bounds[0])} - ${formatTime(bounds[1])} Beijing`;
    const host = document.querySelector('#pod-charts'); host.replaceChildren(); host.classList.toggle('single', selected !== 'all'); charts.length = 0;
    for (const pod of visible) {
      const figure = document.createElement('div'); figure.className = 'pod-plot';
      const stats = data.perPod[pod.name].percent_nonzero.pp0_below_highest;
      figure.innerHTML = `<div class="plot-title"><strong>Pod ${pod.suffix}</strong><span title="Full-window percentage, excluding observations where all four ranks are zero">PP0 below: ${stats.toFixed(1)}%</span></div><div class="chart-box"><canvas role="img" aria-label="Inflight counts for PP0 through PP3 on pod ${pod.suffix}"></canvas></div>`;
      host.append(figure);
      const chart = {canvas: figure.querySelector('canvas'), pod, bounds, yMax}; charts.push(chart); wire(chart); draw(chart);
    }
    window.reportReady = true;
  }
  const examplePod = data.pods.find(p => p.suffix === 'gl76d');
  const marker = Date.parse('2026-08-31T06:06:45+08:00') / 1000;
  const exampleI = data.time.indexOf(marker);
  const exampleVals = examplePod.ranks.map(r => r[exampleI]);
  document.querySelector('#example-values').innerHTML = exampleVals.map((value, rank) => `<div><span style="color:${colors[rank]}">PP${rank}</span><strong>${value}</strong></div>`).join('');
  const detail = {canvas: document.querySelector('#detail'), pod: examplePod, bounds: [marker - 225, marker + 195], yMax: 40, marker};
  wire(detail);
  document.querySelector('#window').addEventListener('change', e => {
    range = e.target.value === 'busy' ? [start + 7200, start + 10800] : e.target.value === 'example' ? [start + 9120, start + 9720] : [start, end];
    document.querySelector('#zoom').value = '1'; document.querySelector('#pan').value = '0'; rebuild();
  });
  for (const id of ['pod', 'zoom']) document.querySelector('#' + id).addEventListener('change', rebuild);
  document.querySelector('#pan').addEventListener('input', rebuild);
  let resizeFrame;
  new ResizeObserver(() => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(() => { for (const chart of charts) draw(chart); draw(detail); }); }).observe(document.querySelector('main'));
  rebuild(); draw(detail);
  window.auditCharts = {charts, detail, classify, redraw: () => { for (const c of charts) draw(c); draw(detail); }};
})();
