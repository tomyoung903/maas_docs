"use strict";

const NS = "http://www.w3.org/2000/svg";
const COLORS = { p50: "#176b87", p90: "#d1842c", p99: "#9d3f56", cached: "#55a77a", uncached: "#54a6c6", total: "#26364a" };

function svgEl(name, attrs = {}, text = null) {
  const node = document.createElementNS(NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  if (text !== null) node.textContent = text;
  return node;
}

function niceMax(value) {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const roughStep = value / 5;
  const power = 10 ** Math.floor(Math.log10(roughStep));
  const scaled = roughStep / power;
  const step = (scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 2.5 ? 2.5 : scaled <= 5 ? 5 : 10) * power;
  return Math.ceil(value / step) * step;
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function fmtM(value) {
  if (!Number.isFinite(value)) return "—";
  return value >= 1e6 ? `${(value / 1e6).toFixed(2)}M` : value >= 1e3 ? `${(value / 1e3).toFixed(1)}K` : Math.round(value).toLocaleString();
}

function fmtS(value) {
  if (!Number.isFinite(value)) return "—";
  return value >= 100 ? `${value.toFixed(0)} s` : value >= 10 ? `${value.toFixed(1)} s` : `${value.toFixed(2)} s`;
}

function fmtPct(value) {
  return Number.isFinite(value) ? `${(100 * value).toFixed(1)}%` : "—";
}

function cstLabel(iso) {
  const date = new Date(iso);
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
}

function baseChart(containerId, rows, maxY, height = 330, yFormatter = value => String(value)) {
  const target = document.getElementById(containerId);
  target.innerHTML = "";
  const width = 1040;
  const margin = { top: 24, right: 24, bottom: 54, left: 72 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });
  const x = index => margin.left + (rows.length === 1 ? innerW / 2 : index * innerW / (rows.length - 1));
  const y = value => margin.top + innerH - Math.max(0, value) * innerH / maxY;
  for (let tick = 0; tick <= 5; tick += 1) {
    const value = maxY * tick / 5;
    const yy = y(value);
    svg.appendChild(svgEl("line", { class: "grid", x1: margin.left, x2: width - margin.right, y1: yy, y2: yy }));
    svg.appendChild(svgEl("text", { x: margin.left - 11, y: yy + 4, "text-anchor": "end" }, yFormatter(value)));
  }
  const labelEvery = Math.max(1, Math.ceil(rows.length / 10));
  rows.forEach((row, index) => {
    if (index % labelEvery !== 0 && index !== rows.length - 1) return;
    svg.appendChild(svgEl("text", { x: x(index), y: height - 23, "text-anchor": "middle" }, cstLabel(row.end_utc)));
  });
  svg.appendChild(svgEl("text", { class: "axis-label", x: margin.left, y: height - 6 }, "CST · interval end"));
  return { target, svg, width, height, margin, innerW, innerH, x, y };
}

function lineChart(containerId, rows, series, options = {}) {
  const values = rows.flatMap(row => series.map(item => finiteOrNull(row[item.key]))).filter(value => value !== null);
  const maxY = options.maxY || niceMax((values.length ? Math.max(...values) : 1) * 1.04);
  const chart = baseChart(containerId, rows, maxY, options.height || 330, options.yFormatter);
  series.forEach(item => {
    let segment = [];
    const flushSegment = () => {
      if (segment.length > 1) {
        chart.svg.appendChild(svgEl("polyline", { points: segment.join(" "), fill: "none", stroke: item.color, "stroke-width": item.width || 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      }
      segment = [];
    };
    rows.forEach((row, index) => {
      const value = finiteOrNull(row[item.key]);
      if (value === null) {
        flushSegment();
        return;
      }
      segment.push(`${chart.x(index)},${chart.y(value)}`);
      const dot = svgEl("circle", { cx: chart.x(index), cy: chart.y(value), r: 3.5, fill: "white", stroke: item.color, "stroke-width": 2 });
      dot.appendChild(svgEl("title", {}, `${cstLabel(row.end_utc)} CST · ${item.label} ${item.tooltip(value)}`));
      chart.svg.appendChild(dot);
    });
    flushSegment();
  });
  chart.target.appendChild(chart.svg);
}

function throughputChart(rows) {
  const maxY = niceMax(Math.max(...rows.map(row => Number(row.prompt_tpm))) * 1.05);
  const chart = baseChart("throughput-chart", rows, maxY, 350, value => `${(value / 1e6).toFixed(0)}M`);
  const slot = chart.innerW / rows.length;
  const barW = Math.max(10, Math.min(42, slot * .64));
  rows.forEach((row, index) => {
    const center = chart.margin.left + slot * (index + .5);
    const uncached = Number(row.uncached_tpm);
    const cached = Number(row.cached_tpm);
    const base = chart.y(0);
    const uncachedY = chart.y(uncached);
    const totalY = chart.y(uncached + cached);
    const uncachedBar = svgEl("rect", { x: center - barW / 2, y: uncachedY, width: barW, height: base - uncachedY, rx: 2, fill: COLORS.uncached });
    uncachedBar.appendChild(svgEl("title", {}, `${cstLabel(row.end_utc)} CST · uncached ${fmtM(uncached)} TPM`));
    chart.svg.appendChild(uncachedBar);
    const cachedBar = svgEl("rect", { x: center - barW / 2, y: totalY, width: barW, height: uncachedY - totalY, rx: 2, fill: COLORS.cached });
    cachedBar.appendChild(svgEl("title", {}, `${cstLabel(row.end_utc)} CST · cached ${fmtM(cached)} TPM`));
    chart.svg.appendChild(cachedBar);
  });
  const linePoints = rows.map((row, index) => {
    const center = chart.margin.left + slot * (index + .5);
    return `${center},${chart.y(Number(row.prompt_tpm))}`;
  }).join(" ");
  chart.svg.appendChild(svgEl("polyline", { points: linePoints, fill: "none", stroke: COLORS.total, "stroke-width": 2.7, "stroke-linejoin": "round" }));
  rows.forEach((row, index) => {
    const center = chart.margin.left + slot * (index + .5);
    const dot = svgEl("circle", { cx: center, cy: chart.y(Number(row.prompt_tpm)), r: 3, fill: COLORS.total });
    dot.appendChild(svgEl("title", {}, `${cstLabel(row.end_utc)} CST · total ${fmtM(Number(row.prompt_tpm))} TPM`));
    chart.svg.appendChild(dot);
  });
  chart.target.appendChild(chart.svg);
}

function renderTable(rows) {
  const body = document.getElementById("minute-rows");
  body.innerHTML = "";
  rows.forEach(row => {
    const tr = document.createElement("tr");
    const cells = [
      `${cstLabel(row.end_utc)} CST · ${row.label_utc} UTC`,
      Number(row.successful_rpm).toLocaleString(),
      fmtS(finiteOrNull(row.ttft_p50_seconds)),
      fmtS(finiteOrNull(row.ttft_p90_seconds)),
      fmtS(finiteOrNull(row.ttft_p99_seconds)),
      fmtPct(finiteOrNull(row.cache_hit)),
      fmtM(Number(row.uncached_tpm)),
      fmtM(Number(row.cached_tpm)),
      fmtM(Number(row.prompt_tpm)),
    ];
    cells.forEach(value => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function render(data) {
  const rows = data.timeseries_60s;
  const summary = data.summary;
  document.getElementById("hero-ttft").textContent = fmtS(Number(summary.ttft_p50_seconds));
  document.getElementById("hero-ttft-detail").textContent = `P90 ${fmtS(Number(summary.ttft_p90_seconds))} · P99 ${fmtS(Number(summary.ttft_p99_seconds))}`;
  document.getElementById("hero-cache").textContent = fmtPct(Number(summary.weighted_cache_hit));
  document.getElementById("hero-uncached").textContent = fmtM(Number(summary.mean_uncached_tpm));
  document.getElementById("hero-uncached-detail").textContent = `mean across all ${data.run.complete_minutes} shown minutes, including gaps`;
  document.getElementById("hero-total").textContent = fmtM(Number(summary.mean_prompt_tpm));
  document.getElementById("hero-request-detail").textContent = `${Number(summary.successful_requests).toLocaleString()} successful requests with exact TTFT`;
  document.getElementById("run-window").textContent = `${data.run.complete_minutes} min`;
  document.getElementById("run-window-detail").textContent = `${cstLabel(data.run.window_start_utc)}–${cstLabel(data.run.window_end_utc)} CST · ${data.run.window_start_utc.slice(11,16)}–${data.run.window_end_utc.slice(11,16)} UTC`;
  const noTtft = Number(summary.status_success_without_ttft);
  const terminated = Number(summary.terminated_inflight_requests);
  document.getElementById("traffic-outcome").textContent = `${Number(summary.successful_requests).toLocaleString()} TTFT · ${Number(summary.failed_requests).toLocaleString()} errors · ${(noTtft + terminated).toLocaleString()} no-TTFT / terminated`;
  document.getElementById("generated-at").textContent = `Generated ${data.generated_at_utc}`;
  document.getElementById("minute-row-count").textContent = `${rows.length} one-minute rows`;

  lineChart("ttft-chart", rows, [
    { key: "ttft_p50_seconds", label: "P50", color: COLORS.p50, tooltip: fmtS },
    { key: "ttft_p90_seconds", label: "P90", color: COLORS.p90, tooltip: fmtS },
    { key: "ttft_p99_seconds", label: "P99", color: COLORS.p99, tooltip: fmtS },
  ], { yFormatter: value => fmtS(value), height: 350 });
  lineChart("cache-chart", rows, [
    { key: "cache_hit", label: "Cache hit", color: COLORS.cached, width: 3.5, tooltip: fmtPct },
  ], { maxY: 1, yFormatter: value => `${Math.round(100 * value)}%`, height: 285 });
  throughputChart(rows);
  renderTable(rows);
}

fetch("analysis.json", { cache: "no-store" })
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(render)
  .catch(error => {
    document.querySelectorAll(".fallback").forEach(node => { node.textContent = `Chart unavailable: ${error.message}`; });
  });
