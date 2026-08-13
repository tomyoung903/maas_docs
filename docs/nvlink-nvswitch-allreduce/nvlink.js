(() => {
  "use strict";

  const story = document.querySelector("[data-story]");
  if (!story) return;

  const SVG_NS = "http://www.w3.org/2000/svg";
  const topology = story.querySelector("[data-topology]");
  const linkLayer = story.querySelector("[data-link-layer]");
  const fabricLayer = story.querySelector("[data-fabric-layer]");
  const flowLayer = story.querySelector("[data-flow-layer]");
  const gpuLayer = story.querySelector("[data-gpu-layer]");
  const packetLayer = story.querySelector("[data-packet-layer]");
  const rankSelect = story.querySelector("[data-rank-select]");
  const previousButton = story.querySelector("[data-previous]");
  const playButton = story.querySelector("[data-play]");
  const nextButton = story.querySelector("[data-next]");
  const replayButton = story.querySelector("[data-replay]");
  const stepButtons = [...story.querySelectorAll("[data-step]")];
  const stepCount = story.querySelector("[data-step-count]");
  const progress = story.querySelector("[data-progress]");
  const progressFill = story.querySelector("[data-progress-fill]");
  const motionLabel = story.querySelector("[data-motion-label]");
  const modeBadge = story.querySelector("[data-mode-badge]");
  const ledgerRank = story.querySelector("[data-ledger-rank]");
  const txValue = story.querySelector("[data-tx-value]");
  const rxValue = story.querySelector("[data-rx-value]");
  const txTrack = story.querySelector("[data-tx-track]");
  const rxTrack = story.querySelector("[data-rx-track]");
  const narrationStep = story.querySelector("[data-narration-step]");
  const narrationTitle = story.querySelector("[data-narration-title]");
  const narrationBody = story.querySelector("[data-narration-body]");
  const equation = story.querySelector("[data-equation]");
  const watchFor = story.querySelector("[data-watch-for]");
  const liveRegion = story.querySelector("[data-live-region]");
  const matrix = document.querySelector("[data-matrix]");
  const cellTitle = document.querySelector("[data-cell-title]");
  const cellCopy = document.querySelector("[data-cell-copy]");
  const cellSource = document.querySelector("[data-cell-source]");
  const cellDestination = document.querySelector("[data-cell-destination]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const gpuPositions = [
    { x: 106, y: 91, side: "left" },
    { x: 106, y: 247, side: "left" },
    { x: 106, y: 403, side: "left" },
    { x: 106, y: 559, side: "left" },
    { x: 994, y: 91, side: "right" },
    { x: 994, y: 247, side: "right" },
    { x: 994, y: 403, side: "right" },
    { x: 994, y: 559, side: "right" },
  ];

  const sceneDuration = 6600;
  const packetDuration = 4100;
  let currentScene = 0;
  let focusRank = 0;
  let selectedDestination = 1;
  let selectedSource = 0;
  let playing = false;
  let replayOnly = false;
  let sceneElapsed = 0;
  let packetClock = packetDuration * 0.38;
  let lastFrame = 0;
  let frameId = 0;
  let storyVisible = false;
  let firstEntrance = true;
  let flowRecords = [];
  let fabricCounter = null;

  const svg = (tag, attributes = {}, text = "") => {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
    if (text) node.textContent = text;
    return node;
  };

  const mathTensor = (rank) => `<span class="math-vec sym-tensor">S<sub>${rank}</sub></span>`;
  const mathTransfer = (source, destination, className = "sym-out") => (
    `<span class="math-vec ${className}">S<sub>${source}→${destination}</sub></span>`
  );
  const multipleS = (count) => `<span class="math-num">${count}<span class="math-var">S</span></span>`;

  const endpointPoint = (rank) => {
    const position = gpuPositions[rank];
    return {
      x: position.side === "left" ? position.x + 77 : position.x - 77,
      y: position.y,
    };
  };

  const portPoint = (rank) => {
    const side = gpuPositions[rank].side;
    const localRank = side === "left" ? rank : rank - 4;
    return {
      x: side === "left" ? 390 : 710,
      y: 151 + localRank * 104,
    };
  };

  const routePath = (source, destination) => {
    const start = endpointPoint(source);
    const finish = endpointPoint(destination);
    const entry = portPoint(source);
    const exit = portPoint(destination);
    const sourceDirection = gpuPositions[source].side === "left" ? 1 : -1;
    const destinationDirection = gpuPositions[destination].side === "left" ? -1 : 1;
    const laneOffset = (((source * 7 + destination) % 7) - 3) * 4;

    return [
      `M ${start.x} ${start.y}`,
      `C ${start.x + sourceDirection * 82} ${start.y}, ${entry.x - sourceDirection * 46} ${entry.y}, ${entry.x} ${entry.y}`,
      `C ${485} ${entry.y + laneOffset}, ${615} ${exit.y - laneOffset}, ${exit.x} ${exit.y}`,
      `C ${exit.x + destinationDirection * 46} ${exit.y}, ${finish.x - destinationDirection * 82} ${finish.y}, ${finish.x} ${finish.y}`,
    ].join(" ");
  };

  const renderFabric = () => {
    fabricLayer.replaceChildren();

    const shell = svg("rect", { x: 390, y: 105, width: 320, height: 440, rx: 20, class: "fabric-shell" });
    const inner = svg("rect", { x: 414, y: 131, width: 272, height: 360, rx: 12, class: "fabric-inner" });
    fabricLayer.append(shell, inner);

    [[447, 202], [573, 202], [447, 331], [573, 331]].forEach(([x, y], index) => {
      const chip = svg("g", { class: "fabric-chip-group" });
      chip.append(
        svg("rect", { x, y, width: 80, height: 77, rx: 9, class: "fabric-chip" }),
        svg("rect", { x: x + 13, y: y + 13, width: 54, height: 41, rx: 5, class: "fabric-chip-core" }),
        svg("circle", { cx: x + 21, cy: y + 65, r: 2.3, class: "fabric-chip-light", style: `animation-delay:${index * 170}ms` }),
        svg("circle", { cx: x + 31, cy: y + 65, r: 2.3, class: "fabric-chip-light", style: `animation-delay:${index * 170 + 80}ms` })
      );
      fabricLayer.append(chip);
    });

    fabricLayer.append(
      svg("text", { x: 550, y: 170, class: "fabric-title" }, "NVSwitch fabric"),
      svg("text", { x: 550, y: 187, class: "fabric-subtitle" }, "routes destination-tagged transactions"),
      svg("rect", { x: 447, y: 506, width: 206, height: 23, rx: 11.5, class: "fabric-inner" })
    );
    fabricCounter = svg("text", { x: 550, y: 521, class: "fabric-counter" }, "0 remote routes");
    fabricLayer.append(fabricCounter);
  };

  const renderStaticLinks = () => {
    linkLayer.replaceChildren();
    for (let rank = 0; rank < 8; rank += 1) {
      const endpoint = endpointPoint(rank);
      const port = portPoint(rank);
      const direction = gpuPositions[rank].side === "left" ? 1 : -1;
      linkLayer.append(svg("path", {
        d: `M ${endpoint.x} ${endpoint.y} C ${endpoint.x + direction * 80} ${endpoint.y}, ${port.x - direction * 45} ${port.y}, ${port.x} ${port.y}`,
        class: "static-link",
      }));
      linkLayer.append(svg("circle", { cx: port.x, cy: port.y, r: 3, class: "port-mark" }));
    }
  };

  const tensorLabel = (rank, x, y) => {
    const text = svg("text", { x, y, class: "tensor-text" });
    text.append(document.createTextNode("S"));
    text.append(svg("tspan", { "baseline-shift": "sub", "font-size": 9 }, String(rank)));
    return text;
  };

  const renderGpus = () => {
    gpuLayer.replaceChildren();
    gpuPositions.forEach((position, rank) => {
      const group = svg("g", { class: "gpu-card", "data-gpu-rank": rank });
      group.append(
        svg("rect", { x: position.x - 72, y: position.y - 39, width: 144, height: 78, rx: 10, class: "gpu-body" }),
        svg("text", { x: position.x - 56, y: position.y - 13, class: "gpu-rank" }, `GPU ${rank}`),
        svg("text", { x: position.x - 56, y: position.y + 5, class: "gpu-memory-label" }, "LOCAL HBM"),
        svg("rect", { x: position.x + 18, y: position.y - 22, width: 39, height: 36, rx: 6, class: "tensor-box" }),
        tensorLabel(rank, position.x + 37.5, position.y + 1),
        svg("circle", {
          cx: position.side === "left" ? position.x + 72 : position.x - 72,
          cy: position.y,
          r: 4,
          class: "port-mark",
        })
      );
      gpuLayer.append(group);
    });
  };

  const setGpuStates = () => {
    [...gpuLayer.querySelectorAll(".gpu-card")].forEach((gpu, rank) => {
      gpu.classList.toggle("gpu-focus", rank === focusRank);
      const activePeer = currentScene === 1
        ? rank === selectedDestination
        : currentScene >= 2 && rank !== focusRank;
      gpu.classList.toggle("gpu-active-peer", activePeer);
    });
  };

  const sceneFlows = () => {
    if (currentScene === 0) return [];
    if (currentScene === 1) return [{ source: focusRank, destination: selectedDestination }];
    if (currentScene === 2) {
      return Array.from({ length: 8 }, (_, destination) => ({ source: focusRank, destination }))
        .filter((flow) => flow.destination !== focusRank);
    }
    if (currentScene === 3 || currentScene === 5) {
      const flows = [];
      for (let peer = 0; peer < 8; peer += 1) {
        if (peer === focusRank) continue;
        flows.push({ source: focusRank, destination: peer });
        flows.push({ source: peer, destination: focusRank });
      }
      return flows;
    }

    const flows = [];
    for (let source = 0; source < 8; source += 1) {
      for (let destination = 0; destination < 8; destination += 1) {
        if (source !== destination) flows.push({ source, destination });
      }
    }
    return flows;
  };

  const flowClass = (source, destination) => {
    if (source === focusRank) return "flow-out";
    if (destination === focusRank) return "flow-in";
    return "flow-peer";
  };

  const packetLabel = (source, destination) => {
    if (currentScene === 1) return `S${source}→${destination}`;
    if (currentScene === 2) return `→${destination}`;
    if (currentScene === 3 || currentScene === 5) {
      return source === focusRank ? `→${destination}` : `${source}→`;
    }
    return "";
  };

  const renderFlows = () => {
    flowLayer.replaceChildren();
    packetLayer.replaceChildren();
    flowRecords = [];

    const flows = sceneFlows();
    flows.forEach((flow, index) => {
      const classification = flowClass(flow.source, flow.destination);
      const selected = flow.source === selectedSource && flow.destination === selectedDestination;
      const path = svg("path", {
        d: routePath(flow.source, flow.destination),
        class: `flow-path ${classification}${selected ? " selected-flow" : ""}`,
        "data-source": flow.source,
        "data-destination": flow.destination,
      });
      flowLayer.append(path);

      const packet = svg("g", { class: `packet-group ${classification}`, "aria-hidden": "true" });
      const label = packetLabel(flow.source, flow.destination);
      if (label) {
        const width = currentScene === 1 ? 43 : 29;
        packet.append(
          svg("rect", { x: -width / 2, y: -10, width, height: 20, rx: 7, class: `packet-tag-bg ${classification}` }),
          svg("text", { x: 0, y: 3, class: "packet-tag" }, label)
        );
      } else {
        packet.append(svg("circle", {
          cx: 0,
          cy: 0,
          r: classification === "flow-peer" ? 2.7 : 5.4,
          class: `packet-dot ${classification}`,
        }));
      }
      packetLayer.append(packet);

      flowRecords.push({
        ...flow,
        classification,
        path,
        packet,
        length: path.getTotalLength(),
        delay: ((index * 0.119) + (flow.source * 0.031)) % 1,
      });
    });

    renderPacketPositions();
  };

  const renderPacketPositions = () => {
    const cycle = packetClock / packetDuration;
    flowRecords.forEach((record) => {
      const phase = (cycle + record.delay) % 1;
      const eased = phase < 0.08
        ? phase / 0.08 * 0.035
        : phase > 0.92
          ? 0.965 + (phase - 0.92) / 0.08 * 0.035
          : 0.035 + (phase - 0.08) / 0.84 * 0.93;
      const point = record.path.getPointAtLength(record.length * eased);
      record.packet.setAttribute("transform", `translate(${point.x.toFixed(2)} ${point.y.toFixed(2)})`);
      record.packet.style.opacity = String(Math.min(1, phase * 9, (1 - phase) * 9));
    });
  };

  const tracePeers = () => Array.from({ length: 8 }, (_, rank) => rank).filter((rank) => rank !== focusRank);

  const renderTrace = () => {
    txTrack.replaceChildren();
    rxTrack.replaceChildren();
    const peers = tracePeers();
    peers.forEach((peer, index) => {
      const tx = document.createElement("span");
      tx.className = "trace-ticket tx";
      tx.style.setProperty("--ticket-index", index);
      tx.innerHTML = `S<sub>${focusRank}→${peer}</sub>`;
      const txActive = currentScene >= 2 || (currentScene === 1 && peer === selectedDestination);
      tx.classList.toggle("active", txActive);
      txTrack.append(tx);

      const rx = document.createElement("span");
      rx.className = "trace-ticket rx";
      rx.style.setProperty("--ticket-index", index);
      rx.innerHTML = `S<sub>${peer}→${focusRank}</sub>`;
      rx.classList.toggle("active", currentScene >= 3);
      rxTrack.append(rx);
    });
  };

  const equationLines = (kicker, lines) => [
    `<span class="equation-kicker">${kicker}</span>`,
    ...lines.map(([left, right]) => (
      `<div class="equation-line"><span class="lhs">${left}</span><span class="equals">=</span><span>${right}</span></div>`
    )),
  ].join("");

  const sceneCopy = () => {
    const peer = selectedDestination;
    const rank = focusRank;
    const scenes = [
      {
        badge: "Local HBM only",
        counter: "0 remote routes",
        tx: "0",
        rx: "0",
        step: "Step 1 · Before communication",
        title: "Eight ranks, eight different partials",
        body: `<p>GPU <strong>${rank}</strong> owns ${mathTensor(rank)}. The other seven GPUs own different partial tensors. No rank yet has the complete tensor-parallel sum.</p><p>The diagonal matrix entries are local reads. They never cross NVLink.</p>`,
        equation: equationLines("Initial state", [
          [`GPU ${rank} HBM`, mathTensor(rank)],
          ["remote payload", `<span class="math-num">0 bytes</span>`],
        ]),
        watch: "The switch is idle. Each partial tensor exists only in its owner’s HBM.",
      },
      {
        badge: `One route · GPU ${rank} → GPU ${peer}`,
        counter: "1 directed route",
        tx: "S",
        rx: "0",
        step: "Step 2 · One matrix cell",
        title: "One payload, named at both ends",
        body: `<p>${mathTransfer(rank, peer)} crosses the fabric exactly once. At GPU ${rank}, that event is <strong class="tx-text">outbound</strong>. At GPU ${peer}, the same event is <strong class="rx-text">inbound</strong>.</p><p>Those endpoint labels do not create two copies. They describe the source and destination of one directed matrix cell.</p>`,
        equation: equationLines("One directed transfer", [
          ["unique payload", mathTransfer(rank, peer)],
          [`GPU ${rank} boundary`, `<span class="tx-text">+<span class="math-var">S</span> TX</span>`],
          [`GPU ${peer} boundary`, `<span class="rx-text">+<span class="math-var">S</span> RX</span>`],
        ]),
        watch: "The same moving ticket is observed at both endpoint boundaries; no duplicate appears inside the switch.",
      },
      {
        badge: `Fan-out from GPU ${rank} · 7 unicasts`,
        counter: `7 routes sourced by GPU ${rank}`,
        tx: "7S",
        rx: "0",
        step: "Step 3 · One complete source row",
        title: "Seven destinations require seven tickets",
        body: `<p>Every peer needs ${mathTensor(rank)}. The traced Lamport kernel loops over all rank buffers: one store is local and seven stores create destination-specific remote transactions.</p><p>The fabric routes each ticket. This function does <strong>not</strong> issue an NVLS <code>multimem</code> operation.</p>`,
        equation: equationLines(`GPU ${rank} source row`, [
          ["destinations", `<span class="math-num">7 peers</span>`],
          ["outbound payload", multipleS(7)],
          ["per destination", `<span class="math-var">S</span>`],
        ]),
        watch: `Count the seven orange tickets as they cross GPU ${rank}’s transmit boundary before taking different routes.`,
      },
      {
        badge: `GPU ${rank} endpoint · simultaneous TX + RX`,
        counter: `14 routes touch GPU ${rank}`,
        tx: "7S",
        rx: "7S",
        step: "Step 4 · Row and column together",
        title: "The return traffic carries different tensors",
        body: `<p>While GPU ${rank} serves ${mathTensor(rank)} to seven peers, it receives ${tracePeers().map((item) => mathTensor(item)).join(", ")} from those peers.</p><p>TX and RX can overlap in time because NVLink is full duplex. They still carry distinct payloads over distinct directional resources.</p>`,
        equation: equationLines(`GPU ${rank} endpoint`, [
          ["outbound row", multipleS(7)],
          ["inbound column", multipleS(7)],
          ["endpoint aggregate", multipleS(14)],
        ]),
        watch: "Orange and teal move simultaneously. Simultaneity shares time—not bytes or direction-specific capacity.",
      },
      {
        badge: "All ranks · 56 directed routes",
        counter: "56 unique directed routes",
        tx: "7S",
        rx: "7S",
        step: "Step 5 · The complete off-diagonal matrix",
        title: "Eight source rows make 56 transfers",
        body: `<p>Repeat the seven-copy source row for all eight ranks. The result is <strong>56 unique directed payloads</strong>: every ordered pair of different GPUs.</p><p>Endpoint accounting observes each transfer once at its source and once at its destination, yielding 112 endpoint-direction observations—but still only 56 unique transfers.</p>`,
        equation: equationLines("Whole-node traffic", [
          ["source rows", `<span class="math-num">8 × 7</span>`],
          ["unique payload", multipleS(56)],
          ["endpoint observations", multipleS(112)],
        ]),
        watch: "Gray peer-to-peer routes complete the matrix; the focused orange row and teal column remain highlighted.",
      },
      {
        badge: "Matched numerator ↔ denominator",
        counter: "same utilization, two ledgers",
        tx: "7S",
        rx: "7S",
        step: "Step 6 · Correct bandwidth accounting",
        title: "Choose one ledger and stay inside it",
        body: `<p>For one direction, divide ${multipleS(7)} by elapsed time and compare with approximately <strong>450 GB/s</strong>. For endpoint aggregate, divide ${multipleS(14)} by the same elapsed time and compare with <strong>900 GB/s</strong>.</p><p>Using the traced 129.7205 µs average gives 66.31 GB/s per direction, or 132.62 GB/s aggregate. Both conventions produce 14.74%.</p>`,
        equation: equationLines("Matched conventions", [
          ["TX-only", `${multipleS(7)} / <span class="math-var">t</span> ↔ 450 GB/s`],
          ["TX + RX", `${multipleS(14)} / <span class="math-var">t</span> ↔ 900 GB/s`],
          ["trace reading", `<span class="math-num">66.31 + 66.31 ≈ 132.62 GB/s</span>`],
        ]),
        watch: "132.62 GB/s aggregate means roughly 66.31 GB/s in each direction—not 132.62 GB/s in each direction.",
      },
    ];
    return scenes[currentScene];
  };

  const renderNarration = () => {
    const copy = sceneCopy();
    modeBadge.textContent = copy.badge;
    if (fabricCounter) fabricCounter.textContent = copy.counter;
    ledgerRank.textContent = `GPU ${focusRank} endpoint`;
    txValue.innerHTML = copy.tx === "7S" ? `7<span class="math-var">S</span>` : copy.tx === "S" ? `<span class="math-var">S</span>` : copy.tx;
    rxValue.innerHTML = copy.rx === "7S" ? `7<span class="math-var">S</span>` : copy.rx;
    narrationStep.textContent = copy.step;
    narrationTitle.textContent = copy.title;
    narrationBody.innerHTML = copy.body;
    equation.innerHTML = copy.equation;
    watchFor.textContent = copy.watch;
  };

  const updateMatrixInspector = () => {
    cellTitle.innerHTML = mathTransfer(selectedSource, selectedDestination);
    cellCopy.textContent = `GPU ${selectedSource}’s partial tensor crosses the fabric once and arrives at GPU ${selectedDestination}.`;
    cellSource.textContent = `GPU ${selectedSource} · outbound`;
    cellDestination.textContent = `GPU ${selectedDestination} · inbound`;
  };

  const updateMatrixClasses = () => {
    if (!matrix) return;
    matrix.querySelectorAll(".matrix-column-label").forEach((label) => {
      label.classList.toggle("focus-column", Number(label.dataset.rank) === focusRank);
    });
    matrix.querySelectorAll(".matrix-row-label").forEach((label) => {
      label.classList.toggle("focus-row", Number(label.dataset.rank) === focusRank);
    });
    matrix.querySelectorAll(".matrix-cell").forEach((cell) => {
      const source = Number(cell.dataset.source);
      const destination = Number(cell.dataset.destination);
      cell.classList.toggle("focus-out", source === focusRank && destination !== focusRank);
      cell.classList.toggle("focus-in", destination === focusRank && source !== focusRank);
      cell.classList.toggle("selected", source === selectedSource && destination === selectedDestination);
    });
    updateMatrixInspector();
  };

  const buildMatrix = () => {
    if (!matrix) return;
    matrix.replaceChildren();
    matrix.append(document.createElement("span"));
    for (let destination = 0; destination < 8; destination += 1) {
      const label = document.createElement("span");
      label.className = "matrix-label matrix-column-label";
      label.dataset.rank = destination;
      label.textContent = `G${destination}`;
      matrix.append(label);
    }
    for (let source = 0; source < 8; source += 1) {
      const rowLabel = document.createElement("span");
      rowLabel.className = "matrix-label matrix-row-label";
      rowLabel.dataset.rank = source;
      rowLabel.textContent = `G${source}`;
      matrix.append(rowLabel);
      for (let destination = 0; destination < 8; destination += 1) {
        const cell = document.createElement("button");
        cell.type = "button";
        cell.className = "matrix-cell";
        cell.dataset.source = source;
        cell.dataset.destination = destination;
        if (source === destination) {
          cell.classList.add("diagonal");
          cell.disabled = true;
          cell.textContent = "local";
          cell.setAttribute("aria-label", `GPU ${source} local HBM read; no NVLink transfer`);
        } else {
          cell.innerHTML = `S<sub>${source}→${destination}</sub><span class="cell-arrow" aria-hidden="true">↗</span>`;
          cell.setAttribute("aria-label", `Select the transfer from GPU ${source} to GPU ${destination}`);
          cell.addEventListener("click", () => {
            focusRank = source;
            selectedSource = source;
            selectedDestination = destination;
            rankSelect.value = String(source);
            setScene(1, { announce: true, keepPlaying: false });
            updateMatrixClasses();
            story.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "center" });
          });
        }
        matrix.append(cell);
      }
    }
    updateMatrixClasses();
  };

  const updateProgress = (fraction) => {
    const bounded = Math.max(0, Math.min(1, fraction));
    const percent = Math.round(bounded * 100);
    progressFill.style.width = `${percent}%`;
    progress.setAttribute("aria-valuenow", String(percent));
  };

  const updateControls = () => {
    stepButtons.forEach((button, index) => {
      const selected = index === currentScene;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    previousButton.disabled = currentScene === 0;
    nextButton.disabled = currentScene === stepButtons.length - 1;
    stepCount.textContent = `Step ${currentScene + 1} of ${stepButtons.length}`;
    playButton.setAttribute("aria-pressed", String(playing));
    playButton.textContent = reducedMotion.matches ? "Motion off" : playing ? "Pause" : "Play tour";
    playButton.disabled = reducedMotion.matches;
    replayButton.disabled = reducedMotion.matches;
    motionLabel.textContent = reducedMotion.matches ? "reduced motion" : playing ? "playing" : "paused";
    story.classList.toggle("is-playing", playing && !reducedMotion.matches);
  };

  const stopFrame = () => {
    if (frameId) cancelAnimationFrame(frameId);
    frameId = 0;
    lastFrame = 0;
  };

  const pause = ({ announce = false } = {}) => {
    playing = false;
    replayOnly = false;
    stopFrame();
    updateControls();
    renderPacketPositions();
    if (announce) liveRegion.textContent = `Paused at step ${currentScene + 1}.`;
  };

  const renderScene = () => {
    story.dataset.scene = String(currentScene);
    setGpuStates();
    renderFlows();
    renderTrace();
    renderNarration();
    updateMatrixClasses();
    updateControls();
  };

  const setScene = (nextScene, { announce = true, keepPlaying = false } = {}) => {
    currentScene = Math.max(0, Math.min(stepButtons.length - 1, nextScene));
    sceneElapsed = 0;
    packetClock = packetDuration * 0.08;
    updateProgress(0);
    if (!keepPlaying) {
      playing = false;
      replayOnly = false;
      stopFrame();
    }
    renderScene();
    if (announce) {
      liveRegion.textContent = `Step ${currentScene + 1} of ${stepButtons.length}: ${stepButtons[currentScene].dataset.title}.`;
    }
  };

  const tick = (time) => {
    if (!playing) return;
    if (!lastFrame) lastFrame = time;
    const delta = Math.min(80, time - lastFrame);
    lastFrame = time;
    sceneElapsed += delta;
    packetClock += delta;
    updateProgress(sceneElapsed / sceneDuration);
    renderPacketPositions();

    if (sceneElapsed >= sceneDuration) {
      if (replayOnly) {
        updateProgress(1);
        pause();
        liveRegion.textContent = `Replay of step ${currentScene + 1} complete.`;
        return;
      }
      if (currentScene >= stepButtons.length - 1) {
        updateProgress(1);
        pause();
        liveRegion.textContent = "Animated walkthrough complete.";
        return;
      }
      currentScene += 1;
      sceneElapsed = 0;
      packetClock = 0;
      renderScene();
      liveRegion.textContent = `Step ${currentScene + 1}: ${stepButtons[currentScene].dataset.title}.`;
    }
    frameId = requestAnimationFrame(tick);
  };

  const play = () => {
    if (playing || reducedMotion.matches || !storyVisible) return;
    if (currentScene === stepButtons.length - 1 && sceneElapsed >= sceneDuration) {
      setScene(0, { announce: false, keepPlaying: false });
    }
    playing = true;
    replayOnly = false;
    lastFrame = 0;
    updateControls();
    frameId = requestAnimationFrame(tick);
    liveRegion.textContent = `Playing from step ${currentScene + 1}.`;
  };

  const replay = () => {
    if (reducedMotion.matches || !storyVisible) return;
    stopFrame();
    sceneElapsed = 0;
    packetClock = 0;
    replayOnly = true;
    playing = true;
    updateProgress(0);
    renderScene();
    lastFrame = 0;
    frameId = requestAnimationFrame(tick);
    liveRegion.textContent = `Replaying step ${currentScene + 1}.`;
  };

  stepButtons.forEach((button, index) => {
    button.addEventListener("click", () => setScene(index));
    button.addEventListener("keydown", (event) => {
      let target = null;
      if (event.key === "ArrowRight") target = Math.min(stepButtons.length - 1, index + 1);
      if (event.key === "ArrowLeft") target = Math.max(0, index - 1);
      if (event.key === "Home") target = 0;
      if (event.key === "End") target = stepButtons.length - 1;
      if (target === null) return;
      event.preventDefault();
      stepButtons[target].focus();
      setScene(target);
    });
  });

  previousButton.addEventListener("click", () => setScene(currentScene - 1));
  nextButton.addEventListener("click", () => setScene(currentScene + 1));
  playButton.addEventListener("click", () => {
    if (playing) pause({ announce: true });
    else play();
  });
  replayButton.addEventListener("click", replay);

  rankSelect.addEventListener("change", () => {
    focusRank = Number(rankSelect.value);
    selectedSource = focusRank;
    if (selectedDestination === focusRank) selectedDestination = (focusRank + 1) % 8;
    setScene(currentScene, { announce: true, keepPlaying: playing });
  });

  story.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && playing) {
      event.preventDefault();
      pause({ announce: true });
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && playing) pause();
  });
  window.addEventListener("pagehide", () => pause());

  const handleMotionPreference = () => {
    if (reducedMotion.matches) pause();
    updateControls();
  };
  if (typeof reducedMotion.addEventListener === "function") {
    reducedMotion.addEventListener("change", handleMotionPreference);
  } else if (typeof reducedMotion.addListener === "function") {
    reducedMotion.addListener(handleMotionPreference);
  }

  renderFabric();
  renderStaticLinks();
  renderGpus();
  buildMatrix();
  renderScene();

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      storyVisible = entries[0].isIntersecting;
      if (storyVisible && firstEntrance && !reducedMotion.matches) {
        firstEntrance = false;
        window.setTimeout(play, 420);
      } else if (!storyVisible && playing) {
        pause();
      }
    }, { threshold: 0.16 });
    observer.observe(story);
  } else {
    storyVisible = true;
    firstEntrance = false;
    if (!reducedMotion.matches) window.setTimeout(play, 420);
  }

  window.__nvlinkStory = {
    setScene: (scene) => setScene(Number(scene), { announce: false }),
    setRank: (rank) => {
      focusRank = Math.max(0, Math.min(7, Number(rank)));
      selectedSource = focusRank;
      if (selectedDestination === focusRank) selectedDestination = (focusRank + 1) % 8;
      rankSelect.value = String(focusRank);
      renderScene();
    },
    play,
    pause,
    replay,
  };
})();
