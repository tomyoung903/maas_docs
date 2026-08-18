(function () {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const svgNamespace = "http://www.w3.org/2000/svg";

  const measured = [
    {
      m: 1,
      blockM: 16,
      mTiles: 1,
      ctas: 48,
      coverage: 31.6,
      stages: 12,
      total: 6.976,
      quant: 1.8219,
      gemm: 5.3483,
      explanation: "<strong>At <i>M</i> = 1:</strong> the minimum 16-row tile is mostly padding. One row tile times 48 column tiles creates only 48 useful CTAs, so roughly two thirds of the SM wave has no output tile to claim."
    },
    {
      m: 10,
      blockM: 16,
      mTiles: 1,
      ctas: 48,
      coverage: 31.6,
      stages: 12,
      total: 7.264,
      quant: 1.7536,
      gemm: 5.4944,
      explanation: "<strong>At <i>M</i> = 10:</strong> the launch geometry is identical to <i>M</i> = 1—one row tile and 48 useful CTAs. More of each 16-row tile is useful, but the same fixed launch and pipeline floor remains."
    },
    {
      m: 20,
      blockM: 16,
      mTiles: 2,
      ctas: 96,
      coverage: 63.2,
      stages: 12,
      total: 7.904,
      quant: 1.7877,
      gemm: 5.7813,
      explanation: "<strong>At <i>M</i> = 20:</strong> a second 16-row tile is required. Useful CTA count doubles from 48 to 96, but those tasks mostly occupy SMs that were idle; the work still fits in one wave."
    },
    {
      m: 100,
      blockM: 48,
      mTiles: 3,
      ctas: 144,
      coverage: 94.7,
      stages: 10,
      total: 8.032,
      quant: 1.7717,
      gemm: 6.2144,
      explanation: "<strong>At <i>M</i> = 100:</strong> the JIT selects 48 rows per tile. Three tile rows times 48 tile columns produce 144 useful CTAs—94.7% of one GB300 wave."
    },
    {
      m: 200,
      blockM: 80,
      mTiles: 3,
      ctas: 144,
      coverage: 94.7,
      stages: 9,
      total: 8.064,
      quant: 1.7675,
      gemm: 6.5643,
      explanation: "<strong>At <i>M</i> = 200:</strong> the JIT raises the tile height to 80. That preserves three row tiles and therefore the same 144 useful CTAs; each CTA is heavier, but no second wave appears."
    },
    {
      m: 500,
      blockM: 176,
      mTiles: 3,
      ctas: 144,
      coverage: 94.7,
      stages: 7,
      total: 10.496,
      quant: 1.9477,
      gemm: 8.5451,
      explanation: "<strong>At <i>M</i> = 500:</strong> a 176-row tile still holds the grid to 144 useful CTAs and one wave. Runtime rises because every CTA now performs much more work with a shallower seven-stage pipeline."
    }
  ];

  let selectedMeasuredIndex = 3;
  let sliceTimer = null;

  function makeElement(name, className, text) {
    const element = document.createElement(name);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function initializeCtaLab() {
    const sliceRow = byId("slice-row");
    for (let index = 0; index < 12; index += 1) {
      const slice = makeElement("i");
      slice.setAttribute("aria-hidden", "true");
      sliceRow.appendChild(slice);
    }

    const captions = [
      "<strong>Tile assigned.</strong> The persistent scheduler gives this CTA one output tile; its accumulators start empty.",
      "<strong>TMA load.</strong> A producer role stages the next activation and weight fragments in shared memory while barriers protect reuse.",
      "<strong>Twelve reduction slices.</strong> Since 1536 ÷ 128 = 12, the pipeline advances through twelve <i>K</i> chunks; after fill, load and compute overlap.",
      "<strong>UMMA accumulation.</strong> Tensor Core instructions multiply each staged pair and add the result into the CTA-owned output accumulators.",
      "<strong>BF16 epilogue.</strong> After all twelve slices, the complete accumulator tile is converted and stored as its patch of <b>Y</b>."
    ];

    function paintSlices(count) {
      const slices = Array.from(sliceRow.children);
      slices.forEach((slice, index) => slice.classList.toggle("is-done", index < count));
      byId("slice-count").textContent = count + " / 12";
    }

    function activateStep(step) {
      if (sliceTimer) {
        window.clearInterval(sliceTimer);
        sliceTimer = null;
      }

      const lab = document.querySelector(".cta-lab");
      lab.dataset.activeStep = String(step);
      document.querySelectorAll(".cta-step").forEach((button) => {
        button.classList.toggle("is-active", Number(button.dataset.step) === step);
      });
      byId("cta-caption").innerHTML = captions[step];

      if (step < 2) {
        paintSlices(0);
      } else if (step === 2) {
        let count = 0;
        paintSlices(count);
        sliceTimer = window.setInterval(() => {
          count += 1;
          paintSlices(count);
          if (count >= 12) {
            window.clearInterval(sliceTimer);
            sliceTimer = null;
          }
        }, 90);
      } else {
        paintSlices(12);
      }
    }

    document.querySelectorAll(".cta-step").forEach((button) => {
      button.addEventListener("click", () => activateStep(Number(button.dataset.step)));
    });
    activateStep(0);
  }

  function renderCurveChart() {
    const svg = byId("curve-chart");
    const width = 820;
    const height = 350;
    const left = 70;
    const right = 30;
    const top = 28;
    const bottom = 58;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const yMin = 6.5;
    const yMax = 11;
    const logMax = Math.log10(500);
    const x = (m) => left + (Math.log10(m) / logMax) * plotWidth;
    const y = (time) => top + ((yMax - time) / (yMax - yMin)) * plotHeight;

    svg.innerHTML = "";
    const definitions = document.createElementNS(svgNamespace, "defs");
    const gradient = document.createElementNS(svgNamespace, "linearGradient");
    gradient.id = "curve-fill";
    gradient.setAttribute("x1", "0");
    gradient.setAttribute("y1", "0");
    gradient.setAttribute("x2", "0");
    gradient.setAttribute("y2", "1");
    const stopOne = document.createElementNS(svgNamespace, "stop");
    stopOne.setAttribute("offset", "0%");
    stopOne.setAttribute("stop-color", "#3568b5");
    stopOne.setAttribute("stop-opacity", ".20");
    const stopTwo = document.createElementNS(svgNamespace, "stop");
    stopTwo.setAttribute("offset", "100%");
    stopTwo.setAttribute("stop-color", "#3568b5");
    stopTwo.setAttribute("stop-opacity", "0");
    gradient.append(stopOne, stopTwo);
    definitions.appendChild(gradient);
    svg.appendChild(definitions);

    [7, 8, 9, 10, 11].forEach((tick) => {
      const line = document.createElementNS(svgNamespace, "line");
      line.setAttribute("x1", String(left));
      line.setAttribute("x2", String(width - right));
      line.setAttribute("y1", String(y(tick)));
      line.setAttribute("y2", String(y(tick)));
      line.setAttribute("class", "grid-line");
      svg.appendChild(line);

      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(left - 13));
      label.setAttribute("y", String(y(tick) + 4));
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "axis-text");
      label.textContent = String(tick);
      svg.appendChild(label);
    });

    const xAxis = document.createElementNS(svgNamespace, "line");
    xAxis.setAttribute("x1", String(left));
    xAxis.setAttribute("x2", String(width - right));
    xAxis.setAttribute("y1", String(height - bottom));
    xAxis.setAttribute("y2", String(height - bottom));
    xAxis.setAttribute("class", "axis-line");
    svg.appendChild(xAxis);

    const yAxis = document.createElementNS(svgNamespace, "line");
    yAxis.setAttribute("x1", String(left));
    yAxis.setAttribute("x2", String(left));
    yAxis.setAttribute("y1", String(top));
    yAxis.setAttribute("y2", String(height - bottom));
    yAxis.setAttribute("class", "axis-line");
    svg.appendChild(yAxis);

    measured.forEach((point) => {
      const tick = document.createElementNS(svgNamespace, "line");
      tick.setAttribute("x1", String(x(point.m)));
      tick.setAttribute("x2", String(x(point.m)));
      tick.setAttribute("y1", String(height - bottom));
      tick.setAttribute("y2", String(height - bottom + 5));
      tick.setAttribute("class", "axis-line");
      svg.appendChild(tick);

      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(x(point.m)));
      label.setAttribute("y", String(height - bottom + 21));
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", "axis-text");
      label.textContent = String(point.m);
      svg.appendChild(label);
    });

    const yTitle = document.createElementNS(svgNamespace, "text");
    yTitle.setAttribute("x", "16");
    yTitle.setAttribute("y", String(top + plotHeight / 2));
    yTitle.setAttribute("text-anchor", "middle");
    yTitle.setAttribute("transform", "rotate(-90 16 " + (top + plotHeight / 2) + ")");
    yTitle.setAttribute("class", "axis-title");
    yTitle.textContent = "active union (µs)";
    svg.appendChild(yTitle);

    const xTitle = document.createElementNS(svgNamespace, "text");
    xTitle.setAttribute("x", String(left + plotWidth / 2));
    xTitle.setAttribute("y", String(height - 9));
    xTitle.setAttribute("text-anchor", "middle");
    xTitle.setAttribute("class", "axis-title");
    xTitle.textContent = "M rows (log scale)";
    svg.appendChild(xTitle);

    const points = measured.map((point) => [x(point.m), y(point.total)]);
    const baseline = height - bottom;
    const areaPath = [
      "M " + points[0][0] + " " + baseline,
      "L " + points.map((point) => point[0] + " " + point[1]).join(" L "),
      "L " + points[points.length - 1][0] + " " + baseline,
      "Z"
    ].join(" ");
    const area = document.createElementNS(svgNamespace, "path");
    area.setAttribute("d", areaPath);
    area.setAttribute("class", "curve-area");
    svg.appendChild(area);

    const line = document.createElementNS(svgNamespace, "path");
    line.setAttribute("d", "M " + points.map((point) => point[0] + " " + point[1]).join(" L "));
    line.setAttribute("class", "curve-line");
    svg.appendChild(line);

    measured.forEach((point, index) => {
      const group = document.createElementNS(svgNamespace, "g");
      group.setAttribute("class", "chart-point");
      group.dataset.index = String(index);
      group.setAttribute("role", "button");
      group.setAttribute("tabindex", "0");
      group.setAttribute("aria-label", "Select M equals " + point.m + ", " + point.total.toFixed(3) + " microseconds");

      const halo = document.createElementNS(svgNamespace, "circle");
      halo.setAttribute("cx", String(x(point.m)));
      halo.setAttribute("cy", String(y(point.total)));
      halo.setAttribute("r", "15");
      halo.setAttribute("class", "point-halo");
      group.appendChild(halo);

      const dot = document.createElementNS(svgNamespace, "circle");
      dot.setAttribute("cx", String(x(point.m)));
      dot.setAttribute("cy", String(y(point.total)));
      dot.setAttribute("r", "5");
      dot.setAttribute("class", "point-dot");
      group.appendChild(dot);

      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(x(point.m)));
      label.setAttribute("y", String(y(point.total) - 14));
      label.setAttribute("text-anchor", index === 0 ? "start" : index === measured.length - 1 ? "end" : "middle");
      label.setAttribute("class", "point-label");
      label.textContent = point.total.toFixed(3);
      group.appendChild(label);

      group.addEventListener("click", () => selectMeasured(index));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectMeasured(index);
        }
      });
      svg.appendChild(group);
    });
  }

  function initializeMeasuredExplorer() {
    const buttons = byId("point-buttons");
    measured.forEach((point, index) => {
      const button = makeElement("button", "point-button", "M=" + point.m);
      button.type = "button";
      button.dataset.index = String(index);
      button.addEventListener("click", () => selectMeasured(index));
      buttons.appendChild(button);
    });

    const smGrid = byId("sm-grid");
    for (let index = 0; index < 152; index += 1) {
      const cell = makeElement("i", "sm-cell");
      if (index % 2 === 1) cell.classList.add("cluster-end");
      cell.setAttribute("aria-hidden", "true");
      smGrid.appendChild(cell);
    }

    renderCurveChart();
    selectMeasured(selectedMeasuredIndex);
  }

  function selectMeasured(index) {
    selectedMeasuredIndex = index;
    const point = measured[index];
    document.querySelectorAll(".point-button").forEach((button) => {
      button.classList.toggle("is-active", Number(button.dataset.index) === index);
    });
    document.querySelectorAll(".chart-point").forEach((group) => {
      group.classList.toggle("is-active", Number(group.dataset.index) === index);
    });
    document.querySelectorAll(".evidence-table tbody tr").forEach((row, rowIndex) => {
      row.classList.toggle("highlight-row", rowIndex === index);
    });

    byId("selected-m").textContent = String(point.m);
    byId("selected-time").textContent = point.total.toFixed(3);
    byId("selected-quant").textContent = point.quant.toFixed(3) + " µs";
    byId("selected-gemm").textContent = point.gemm.toFixed(3) + " µs";
    byId("quant-bar").style.width = Math.min(100, point.quant / 10 * 100).toFixed(1) + "%";
    byId("gemm-bar").style.width = Math.min(100, point.gemm / 10 * 100).toFixed(1) + "%";
    byId("selected-bm").textContent = String(point.blockM);
    byId("selected-mtiles").textContent = String(point.mTiles);
    byId("selected-ctas").textContent = String(point.ctas);
    byId("selected-coverage").textContent = point.coverage.toFixed(1) + "%";
    byId("selected-stages").textContent = String(point.stages);
    byId("active-sm-count").textContent = String(point.ctas);
    byId("idle-sm-count").textContent = String(152 - point.ctas);
    byId("tile-shape-label").textContent = point.mTiles + (point.mTiles === 1 ? " row" : " rows") + " × 48 columns";
    byId("point-explanation").innerHTML = point.explanation;

    const outputTiles = byId("output-tiles");
    outputTiles.innerHTML = "";
    for (let tile = 0; tile < point.ctas; tile += 1) {
      const cell = makeElement("i", "output-tile");
      cell.style.animationDelay = Math.min(tile * 2, 220) + "ms";
      cell.setAttribute("aria-hidden", "true");
      outputTiles.appendChild(cell);
    }
    outputTiles.setAttribute("aria-label", point.mTiles + " M tile rows by 48 N tile columns, " + point.ctas + " output tiles");

    Array.from(byId("sm-grid").children).forEach((cell, cellIndex) => {
      cell.classList.toggle("is-active", cellIndex < point.ctas);
      cell.style.animationDelay = cellIndex < point.ctas ? Math.min(cellIndex * 1.5, 160) + "ms" : "0ms";
      cell.title = cellIndex < point.ctas ? "SM slot " + (cellIndex + 1) + ": useful CTA" : "SM slot " + (cellIndex + 1) + ": no output tile";
    });
  }

  const layoutRegions = [
    { max: 16, blockM: 16 },
    { max: 32, blockM: 16 },
    { max: 48, blockM: 16 },
    { max: 64, blockM: 32 },
    { max: 96, blockM: 32 },
    { max: 144, blockM: 48 },
    { max: 192, blockM: 64 },
    { max: 240, blockM: 80 },
    { max: 288, blockM: 96 },
    { max: 336, blockM: 112 },
    { max: 384, blockM: 128 },
    { max: 432, blockM: 144 },
    { max: 480, blockM: 160 },
    { max: 528, blockM: 176 },
    { max: 576, blockM: 192 },
    { max: 624, blockM: 208 },
    { max: 672, blockM: 224 },
    { max: 720, blockM: 240 },
    { max: 768, blockM: 128 },
    { max: 864, blockM: 144 },
    { max: 960, blockM: 160 }
  ];

  function layoutForM(m) {
    const region = layoutRegions.find((candidate) => m <= candidate.max) || layoutRegions[layoutRegions.length - 1];
    const mTiles = Math.ceil(m / region.blockM);
    const ctas = mTiles * 48;
    const waves = Math.ceil(ctas / 152);
    const coverage = ctas / (waves * 152) * 100;
    return { blockM: region.blockM, mTiles, ctas, waves, coverage };
  }

  function teachingTime(m, layout) {
    const quant = Math.max(1.75, 1.65 + 0.0006 * m);
    const gemm = 5.21 + 0.0188 * layout.waves * layout.blockM;
    return quant + gemm;
  }

  function renderWaveStrips(ctas, waves) {
    const container = byId("wave-strips");
    container.innerHTML = "";
    container.setAttribute("aria-label", ctas + " CTA tasks distributed across " + waves + (waves === 1 ? " scheduling wave" : " scheduling waves"));
    for (let wave = 0; wave < waves; wave += 1) {
      const row = makeElement("div", "wave-row");
      row.appendChild(makeElement("span", "", "wave " + (wave + 1)));
      const slots = makeElement("div", "wave-slots");
      const usedInWave = Math.max(0, Math.min(152, ctas - wave * 152));
      for (let slot = 0; slot < 152; slot += 1) {
        const cell = makeElement("i", "wave-slot" + (slot < usedInWave ? " is-used" : ""));
        cell.setAttribute("aria-hidden", "true");
        slots.appendChild(cell);
      }
      row.appendChild(slots);
      container.appendChild(row);
    }
  }

  function updateShapePredictor() {
    const slider = byId("m-slider");
    const m = Number(slider.value);
    const layout = layoutForM(m);
    const estimate = teachingTime(m, layout);
    const progress = (m - Number(slider.min)) / (Number(slider.max) - Number(slider.min)) * 100;
    slider.style.setProperty("--progress", progress.toFixed(2) + "%");

    byId("forecast-m").textContent = String(m);
    byId("forecast-bm").textContent = String(layout.blockM);
    byId("forecast-mtiles").textContent = String(layout.mTiles);
    byId("forecast-ctas").textContent = String(layout.ctas);
    byId("forecast-waves").textContent = String(layout.waves);
    byId("forecast-coverage").textContent = layout.coverage.toFixed(1) + "%";
    byId("forecast-time").textContent = "≈ " + estimate.toFixed(2) + " µs";

    if (layout.waves === 1) {
      byId("wave-caption").textContent = layout.ctas + " tasks fit inside 152 first-wave slots";
    } else {
      byId("wave-caption").textContent = layout.ctas + " tasks spill across " + layout.waves + " waves";
    }
    renderWaveStrips(layout.ctas, layout.waves);
  }

  function initializeShapePredictor() {
    byId("m-slider").addEventListener("input", updateShapePredictor);
    updateShapePredictor();
  }

  function positiveNumber(input, fallback) {
    const value = Number(input.value);
    return Number.isFinite(value) && value > 0 ? value : fallback;
  }

  function updateCalculator() {
    const form = byId("tile-calculator");
    const m = positiveNumber(form.elements.namedItem("m"), 1);
    const n = positiveNumber(form.elements.namedItem("n"), 1);
    const k = positiveNumber(form.elements.namedItem("k"), 1);
    const blockM = positiveNumber(form.elements.namedItem("bm"), 1);
    const blockN = positiveNumber(form.elements.namedItem("bn"), 1);
    const blockK = positiveNumber(form.elements.namedItem("bk"), 1);
    const sms = positiveNumber(form.elements.namedItem("sms"), 1);
    const resident = positiveNumber(form.elements.namedItem("resident"), 1);
    const mTiles = Math.ceil(m / blockM);
    const nTiles = Math.ceil(n / blockN);
    const kSlices = Math.ceil(k / blockK);
    const ctas = mTiles * nTiles;
    const waveCapacity = sms * resident;
    const waves = Math.max(1, Math.ceil(ctas / waveCapacity));
    const slotFill = ctas / (waves * waveCapacity) * 100;
    const rowExtent = mTiles * blockM;
    const rowFill = m / rowExtent * 100;
    const padding = rowExtent - m;

    byId("calc-m-expression").textContent = "⌈" + m + " / " + blockM + "⌉";
    byId("calc-n-expression").textContent = "⌈" + n + " / " + blockN + "⌉";
    byId("calc-ctas").textContent = ctas.toLocaleString() + " " + (ctas === 1 ? "CTA" : "CTAs");
    byId("calc-waves").textContent = waves + " " + (waves === 1 ? "wave" : "waves");
    byId("calc-mtiles").textContent = mTiles.toLocaleString();
    byId("calc-ntiles").textContent = nTiles.toLocaleString();
    byId("calc-kslices").textContent = kSlices.toLocaleString();
    byId("calc-slot-fill").textContent = slotFill.toFixed(1) + "%";
    byId("calc-row-fill").textContent = rowFill.toFixed(1) + "%";
    byId("calc-padding").textContent = padding.toLocaleString() + " " + (padding === 1 ? "row" : "rows");
  }

  function initializeCalculator() {
    const form = byId("tile-calculator");
    form.addEventListener("input", updateCalculator);
    form.addEventListener("submit", (event) => event.preventDefault());
    byId("reset-calculator").addEventListener("click", () => {
      const defaults = { m: 100, n: 6144, k: 1536, bm: 48, bn: 128, bk: 128, sms: 152, resident: 1 };
      Object.entries(defaults).forEach(([name, value]) => {
        form.elements.namedItem(name).value = String(value);
      });
      updateCalculator();
    });
    updateCalculator();
  }

  function initializeContentsTracking() {
    const links = Array.from(document.querySelectorAll(".toc-link"));
    const sections = links
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    if (!("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === "#" + visible.target.id);
      });
    }, { rootMargin: "-15% 0px -68% 0px", threshold: [0, 0.05, 0.2] });
    sections.forEach((section) => observer.observe(section));
  }

  initializeCtaLab();
  initializeMeasuredExplorer();
  initializeShapePredictor();
  initializeCalculator();
  initializeContentsTracking();
})();
