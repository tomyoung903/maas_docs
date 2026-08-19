(function () {
  "use strict";

  const data = window.GLM52_TOP10_SWEEP;
  if (!data || !Array.isArray(data.records)) {
    document.querySelectorAll(".chart-wrap").forEach((element) => {
      element.textContent = "Report data did not load.";
    });
    return;
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  const COLORS = ["#087f75", "#3d6fa3", "#c14f42", "#b47b16", "#7766a6", "#4d7e52"];
  const ROW_ANCHORS = [32, 100, 192, 512];
  const X_TICKS = [1, 2, 4, 8, 16, 32, 64, 100, 192, 512];

  const metrics = {
    leaf: {
      id: "leaf",
      button: "Exact leaf",
      axis: "Median active interval (µs)",
      unit: "µs",
      value: (record) => record.leaf_status === "ok" ? record.leaf?.median_us : null,
      alternate: (record) => record.leaf_status === "target_missing" ? record.composite_gpu?.median_us : null,
    },
    operator: {
      id: "operator",
      button: "Callable boundary",
      axis: "CUDA-event boundary (µs)",
      unit: "µs",
      value: (record) => record.operator?.median_us,
    },
    composite: {
      id: "composite",
      button: "GPU pair",
      axis: "All-kernel active interval (µs)",
      unit: "µs",
      value: (record) => record.composite_gpu?.median_us,
    },
    tflops: {
      id: "tflops",
      button: "Useful TFLOP/s",
      axis: "Modeled useful throughput (TFLOP/s)",
      unit: "TFLOP/s",
      value: (record) => record.leaf_status === "ok" ? record.leaf_tflops : null,
    },
    quantGbps: {
      id: "quantGbps",
      button: "Useful GB/s",
      axis: "Modeled useful traffic (GB/s)",
      unit: "GB/s",
      value: (record) => record.leaf_gbps,
    },
    gatherRate: {
      id: "gatherRate",
      button: "Gather rate",
      axis: "Gathered elements (million/s)",
      unit: "M elements/s",
      value: (record) => record.gather_melements_s,
    },
    payloadGbps: {
      id: "payloadGbps",
      button: "Payload GB/s",
      axis: "Modeled rank payload (GB/s)",
      unit: "GB/s",
      value: (record) => record.payload_gbps,
    },
  };

  function compactCount(value) {
    if (value >= 1048576 && value % 1048576 === 0) return `${value / 1048576}M`;
    if (value >= 1024 && value % 1024 === 0) return `${value / 1024}K`;
    return String(value);
  }

  const viewSpecs = {
    K1: {
      routing: {
        filter: () => true,
        key: (record) => record.params.active_experts,
        label: (key) => `${key} active experts`,
        order: (key) => Number(key),
      },
    },
    K2: {
      selected: {
        filter: (record) => record.params.context_tokens === 65536,
        key: (record) => record.params.selected_tokens,
        label: (key) => `S=${key}`,
        order: (key) => Number(key),
      },
      context: {
        filter: (record) => record.params.selected_tokens === 2048,
        key: (record) => record.params.context_tokens,
        label: (key) => `C=${compactCount(Number(key))}`,
        order: (key) => Number(key),
      },
    },
    K3: {
      routing: {
        filter: () => true,
        key: (record) => record.params.active_experts,
        label: (key) => `${key} active experts`,
        order: (key) => Number(key),
      },
    },
    K4: {
      tp: {
        filter: () => true,
        key: (record) => record.params.tensor_parallel_size,
        label: (key) => `TP${key}`,
        order: (key) => Number(key),
      },
    },
    K5: {
      width: {
        filter: () => true,
        key: (record) => record.params.width,
        label: (key) => `W=${key}`,
        order: (key) => Number(key),
      },
    },
    K6: {
      rows: {
        filter: () => true,
        key: () => "qkv-a",
        label: () => "N=2624, K=6144",
        order: () => 0,
      },
    },
    K7: {
      tp: {
        filter: () => true,
        key: (record) => record.params.tensor_parallel_size,
        label: (key) => `TP${key}`,
        order: (key) => Number(key),
      },
    },
    K8: {
      selected: {
        filter: (record) => record.params.context_tokens === 1048576 && record.params.index_pattern === "random",
        key: (record) => record.params.selected_tokens,
        label: (key) => `S=${key}`,
        order: (key) => Number(key),
      },
      context: {
        filter: (record) => record.params.selected_tokens === 2048 && record.params.index_pattern === "random",
        key: (record) => record.params.context_tokens,
        label: (key) => `C=${compactCount(Number(key))}`,
        order: (key) => Number(key),
      },
      locality: {
        filter: (record) => record.params.selected_tokens === 2048 && record.params.context_tokens === 1048576,
        key: (record) => record.params.index_pattern,
        label: (key) => key === "contiguous" ? "Contiguous IDs" : "Random IDs",
        order: (key) => key === "contiguous" ? 0 : 1,
      },
    },
    K9: {
      topology: topologyView(),
    },
    K10: {
      topology: topologyView(),
    },
  };

  const kernelMetrics = {
    K1: [metrics.leaf, metrics.operator, metrics.tflops],
    K2: [metrics.leaf, metrics.operator, metrics.tflops],
    K3: [metrics.leaf, metrics.operator, metrics.tflops],
    K4: [metrics.leaf, metrics.operator, metrics.tflops],
    K5: [metrics.leaf, metrics.operator, metrics.quantGbps],
    K6: [metrics.leaf, metrics.operator, metrics.tflops],
    K7: [metrics.leaf, metrics.operator, metrics.tflops],
    K8: [metrics.leaf, metrics.operator, metrics.gatherRate],
    K9: [metrics.leaf, metrics.composite, metrics.payloadGbps],
    K10: [metrics.leaf, metrics.composite, metrics.operator],
  };

  function topologyView() {
    return {
      filter: () => true,
      key: (record) => `tp${record.params.tensor_parallel_size}-${record.node}`,
      label: (key) => {
        const match = /^tp(\d+)-node(\d+)$/.exec(key);
        return match ? `TP${match[1]} · node ${match[2]}` : key;
      },
      order: (key) => {
        const match = /^tp(\d+)-node(\d+)$/.exec(key);
        if (!match) return 9999;
        return Number(match[1]) * 1000 + Number(match[2]);
      },
    };
  }

  function svgElement(name, attributes = {}, text = null) {
    const element = document.createElementNS(SVG_NS, name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    if (text !== null) element.textContent = text;
    return element;
  }

  function finite(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function niceMaximum(value) {
    if (!finite(value) || value <= 0) return 1;
    const exponent = Math.floor(Math.log10(value));
    const base = 10 ** exponent;
    const normalized = value / base;
    const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10;
    return step * base;
  }

  function formatValue(value, metric, axis = false) {
    if (!finite(value)) return "—";
    let digits;
    if (axis) {
      digits = value < 1 ? 2 : value < 10 ? 1 : 0;
    } else {
      digits = value < 10 ? 3 : value < 100 ? 2 : value < 1000 ? 1 : 0;
    }
    return value.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function makeSeries(label, viewId) {
    const spec = viewSpecs[label][viewId];
    const groups = new Map();
    data.records
      .filter((record) => record.label === label && spec.filter(record))
      .forEach((record) => {
        const key = String(spec.key(record));
        if (!groups.has(key)) groups.set(key, new Map());
        groups.get(key).set(record.params.local_rows, record);
      });

    return [...groups.entries()]
      .map(([key, byRow]) => ({
        key,
        label: spec.label(key),
        order: spec.order(key),
        records: [...byRow.values()].sort((a, b) => a.params.local_rows - b.params.local_rows),
      }))
      .sort((a, b) => a.order - b.order)
      .map((series, index) => ({ ...series, color: COLORS[index % COLORS.length] }));
  }

  function pathFromPoints(points) {
    return points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
  }

  function parameterSummary(record) {
    const names = {
      active_experts: "experts",
      selected_tokens: "S",
      context_tokens: "C",
      index_pattern: "IDs",
      tensor_parallel_size: "TP",
      width: "W",
    };
    return Object.entries(record.params)
      .filter(([key]) => key !== "local_rows" && Object.prototype.hasOwnProperty.call(names, key))
      .map(([key, value]) => `${names[key]}=${key === "context_tokens" ? compactCount(value) : value}`)
      .join(" · ");
  }

  function showTooltip(section, event, series, record, metric, value, alternate) {
    const tooltip = section.querySelector(".chart-tooltip");
    const wrap = section.querySelector(".chart-wrap");
    const title = document.createElement("strong");
    title.textContent = `${series.label} · M=${record.params.local_rows}`;
    const measurement = document.createElement("span");
    measurement.textContent = alternate
      ? `Alternate leaf GPU interval: ${formatValue(value, metric)} ${metric.unit}`
      : `${metric.axis}: ${formatValue(value, metric)} ${metric.unit}`;
    const params = document.createElement("span");
    params.textContent = parameterSummary(record) || "Fixed production shape";
    const provenance = document.createElement("span");
    provenance.textContent = `${record.node} · ${record.mode}${alternate ? " · target symbol not dispatched" : ""}`;
    tooltip.replaceChildren(title, measurement, params, provenance);
    tooltip.hidden = false;

    const bounds = wrap.getBoundingClientRect();
    const x = Math.min(Math.max(event.clientX - bounds.left + 12, 6), Math.max(6, bounds.width - 222));
    const y = Math.max(6, event.clientY - bounds.top - 74);
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  }

  function hideTooltip(section) {
    section.querySelector(".chart-tooltip").hidden = true;
  }

  function renderLegend(svg, seriesList) {
    const group = svgElement("g", { class: "chart-legend" });
    seriesList.forEach((series, index) => {
      const column = index % 3;
      const row = Math.floor(index / 3);
      const x = 72 + column * 286;
      const y = 22 + row * 22;
      group.appendChild(svgElement("line", { x1: x, y1: y, x2: x + 22, y2: y, stroke: series.color }));
      group.appendChild(svgElement("circle", { cx: x + 11, cy: y, r: 3, fill: series.color }));
      group.appendChild(svgElement("text", { x: x + 30, y: y + 3 }, series.label));
    });
    svg.appendChild(group);
  }

  function renderChart(section, label, viewId, metric) {
    const svg = section.querySelector(".kernel-chart");
    svg.replaceChildren();
    svg.appendChild(svgElement("title", {}, `${label} ${viewId}: ${metric.axis}`));
    const seriesList = makeSeries(label, viewId);
    renderLegend(svg, seriesList);

    const layout = {
      left: 72,
      right: 26,
      top: seriesList.length > 3 ? 72 : 52,
      bottom: 52,
      width: 960,
      height: 430,
    };
    layout.plotWidth = layout.width - layout.left - layout.right;
    layout.plotHeight = layout.height - layout.top - layout.bottom;

    const allValues = [];
    seriesList.forEach((series) => {
      series.records.forEach((record) => {
        const value = metric.value(record);
        const alternate = metric.alternate ? metric.alternate(record) : null;
        if (finite(value)) allValues.push(value);
        if (finite(alternate)) allValues.push(alternate);
      });
    });

    if (allValues.length === 0) {
      svg.appendChild(svgElement("text", { x: 480, y: 220, "text-anchor": "middle", class: "chart-empty" }, "No measured values for this metric."));
      return;
    }

    const yMax = niceMaximum(Math.max(...allValues) * 1.08);
    const xScale = (value) => layout.left + (Math.log2(value) / Math.log2(512)) * layout.plotWidth;
    const yScale = (value) => layout.top + layout.plotHeight - (value / yMax) * layout.plotHeight;

    const grid = svgElement("g", { class: "chart-grid" });
    const axis = svgElement("g", { class: "chart-axis" });
    for (let index = 0; index <= 5; index += 1) {
      const value = yMax * index / 5;
      const y = yScale(value);
      grid.appendChild(svgElement("line", { x1: layout.left, y1: y, x2: layout.width - layout.right, y2: y }));
      axis.appendChild(svgElement("text", { x: layout.left - 10, y: y + 3, "text-anchor": "end" }, formatValue(value, metric, true)));
    }
    X_TICKS.forEach((value) => {
      const x = xScale(value);
      axis.appendChild(svgElement("line", { x1: x, y1: layout.top + layout.plotHeight, x2: x, y2: layout.top + layout.plotHeight + 5 }));
      axis.appendChild(svgElement("text", { x, y: layout.top + layout.plotHeight + 20, "text-anchor": "middle" }, String(value)));
    });
    axis.appendChild(svgElement("line", {
      x1: layout.left,
      y1: layout.top + layout.plotHeight,
      x2: layout.width - layout.right,
      y2: layout.top + layout.plotHeight,
    }));
    svg.appendChild(grid);
    svg.appendChild(axis);
    svg.appendChild(svgElement("text", { x: layout.left, y: layout.top - 12, class: "chart-y-label" }, metric.axis));
    svg.appendChild(svgElement("text", {
      x: layout.left + layout.plotWidth / 2,
      y: layout.height - 12,
      "text-anchor": "middle",
      class: "chart-y-label",
    }, "Local rows M (log scale)"));

    [
      { value: 100, className: "reference", label: "exact pair" },
      { value: 192, className: "production", label: "live estimate" },
    ].forEach((anchor, index) => {
      const x = xScale(anchor.value);
      svg.appendChild(svgElement("line", {
        x1: x,
        y1: layout.top,
        x2: x,
        y2: layout.top + layout.plotHeight,
        class: `chart-anchor-line ${anchor.className}`,
      }));
      svg.appendChild(svgElement("text", {
        x: x + 4,
        y: layout.top + 13 + index * 13,
        class: "chart-anchor-label",
      }, anchor.label));
    });

    seriesList.forEach((series) => {
      const exactPoints = series.records
        .map((record) => ({ record, value: metric.value(record) }))
        .filter((point) => finite(point.value))
        .map((point) => ({
          ...point,
          x: xScale(point.record.params.local_rows),
          y: yScale(point.value),
        }));
      if (exactPoints.length > 1) {
        svg.appendChild(svgElement("path", {
          d: pathFromPoints(exactPoints),
          stroke: series.color,
          class: "chart-series-path",
        }));
      }

      exactPoints.forEach((point) => {
        svg.appendChild(svgElement("circle", {
          cx: point.x,
          cy: point.y,
          r: 3.5,
          fill: series.color,
          class: "chart-series-dot",
        }));
        const hit = svgElement("circle", { cx: point.x, cy: point.y, r: 11, class: "chart-series-hit" });
        hit.addEventListener("pointerenter", (event) => showTooltip(section, event, series, point.record, metric, point.value, false));
        hit.addEventListener("pointermove", (event) => showTooltip(section, event, series, point.record, metric, point.value, false));
        hit.addEventListener("pointerleave", () => hideTooltip(section));
        svg.appendChild(hit);
      });

      if (metric.alternate) {
        series.records.forEach((record) => {
          const value = metric.alternate(record);
          if (!finite(value)) return;
          const x = xScale(record.params.local_rows);
          const y = yScale(value);
          svg.appendChild(svgElement("path", {
            d: `M${x},${y - 5} L${x + 5},${y} L${x},${y + 5} L${x - 5},${y} Z`,
            class: "chart-alternate",
          }));
          const hit = svgElement("circle", { cx: x, cy: y, r: 11, class: "chart-series-hit" });
          hit.addEventListener("pointerenter", (event) => showTooltip(section, event, series, record, metric, value, true));
          hit.addEventListener("pointermove", (event) => showTooltip(section, event, series, record, metric, value, true));
          hit.addEventListener("pointerleave", () => hideTooltip(section));
          svg.appendChild(hit);
        });
      }
    });

    renderTable(section, seriesList, metric);
    const dispatchNote = section.querySelector(".dispatch-note");
    dispatchNote.textContent = label === "K2" && metric.id === "leaf"
      ? "◇ alternate leaf; marker height is the all-kernel GPU interval"
      : "";
  }

  function renderTable(section, seriesList, metric) {
    const table = section.querySelector(".anchor-table");
    const head = table.querySelector("thead");
    const body = table.querySelector("tbody");
    head.replaceChildren();
    body.replaceChildren();

    const headingRow = document.createElement("tr");
    ["Local M", ...seriesList.map((series) => series.label)].forEach((label) => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = label;
      headingRow.appendChild(cell);
    });
    head.appendChild(headingRow);

    ROW_ANCHORS.forEach((rowValue) => {
      const row = document.createElement("tr");
      if (rowValue === 192) row.classList.add("is-production");
      const labelCell = document.createElement("td");
      labelCell.textContent = String(rowValue);
      row.appendChild(labelCell);

      seriesList.forEach((series) => {
        const record = series.records.find((candidate) => candidate.params.local_rows === rowValue);
        const cell = document.createElement("td");
        const value = record ? metric.value(record) : null;
        const alternate = record && metric.alternate ? metric.alternate(record) : null;
        if (finite(value)) {
          cell.textContent = `${formatValue(value, metric)} ${metric.unit}`;
        } else if (finite(alternate)) {
          cell.textContent = `alt ${formatValue(alternate, metric)} ${metric.unit}`;
          cell.classList.add("alternate-cell");
          cell.title = "Target symbol did not dispatch; shown value is the all-kernel GPU active interval.";
        } else {
          cell.textContent = "—";
        }
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
  }

  function renderMetricButtons(section, label, state) {
    const container = section.querySelector(".metric-switch");
    container.replaceChildren();
    kernelMetrics[label].forEach((metric) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.metric = metric.id;
      button.textContent = metric.button;
      if (metric.id === state.metric) button.classList.add("is-active");
      button.addEventListener("click", () => {
        state.metric = metric.id;
        container.querySelectorAll("button").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        renderChart(section, label, state.view, metric);
      });
      container.appendChild(button);
    });
  }

  document.querySelectorAll(".kernel-section").forEach((section) => {
    const label = section.dataset.kernel;
    const viewButton = section.querySelector(".view-switch button.is-active") || section.querySelector(".view-switch button");
    const state = { view: viewButton.dataset.view, metric: "leaf" };
    renderMetricButtons(section, label, state);
    renderChart(section, label, state.view, metrics.leaf);

    section.querySelectorAll(".view-switch button").forEach((button) => {
      button.addEventListener("click", () => {
        state.view = button.dataset.view;
        section.querySelectorAll(".view-switch button").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        const metric = kernelMetrics[label].find((candidate) => candidate.id === state.metric) || metrics.leaf;
        renderChart(section, label, state.view, metric);
      });
    });
  });

  function selectedValue(containerId) {
    const button = document.querySelector(`#${containerId} button.is-active`);
    return Number(button.dataset.value);
  }

  function updateTranslator() {
    const batchInput = document.querySelector("#global-batch");
    const batch = Math.max(1, Number(batchInput.value) || 1);
    const dp = selectedValue("dp-control");
    const draft = selectedValue("draft-control");
    const estimate = Math.ceil(batch / dp) * draft;
    const nearest = data.rows.reduce((best, candidate) => Math.abs(candidate - estimate) < Math.abs(best - estimate) ? candidate : best);
    document.querySelector("#estimated-m").textContent = estimate.toLocaleString("en-US");
    document.querySelector("#nearest-point").textContent = estimate === nearest
      ? `Exact measured point: M=${nearest}`
      : `Nearest measured point: M=${nearest}`;
  }

  document.querySelector("#global-batch").addEventListener("input", updateTranslator);
  ["dp-control", "draft-control"].forEach((id) => {
    document.querySelectorAll(`#${id} button`).forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(`#${id} button`).forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        updateTranslator();
      });
    });
  });
  updateTranslator();

  const tocLinks = [...document.querySelectorAll(".contents nav a")];
  const targetById = new Map(tocLinks.map((link) => [link.getAttribute("href").slice(1), link]));
  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    tocLinks.forEach((link) => link.classList.toggle("is-active", link === targetById.get(visible.target.id)));
  }, { rootMargin: "-15% 0px -70% 0px", threshold: [0, 0.05, 0.2] });
  targetById.forEach((_link, id) => {
    const target = document.getElementById(id);
    if (target) observer.observe(target);
  });
})();
