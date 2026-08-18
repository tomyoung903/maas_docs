(() => {
  "use strict";

  const dataElement = document.getElementById("report-data");
  const report = JSON.parse(dataElement.textContent);
  const treeRoot = document.getElementById("tree-root");
  const search = document.getElementById("tree-search");
  const filterStatus = document.getElementById("filter-status");

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const formatMs = (value) => {
    if (value >= 10) return value.toFixed(3);
    if (value >= 1) return value.toFixed(3);
    if (value >= 0.1) return value.toFixed(4);
    return value.toFixed(5);
  };

  const depthLabel = (node) => ({
    broad_type: `Type ${node.number}`,
    subtype: "Subtype",
    fine_type: "Fine type",
    implementation_signature: "Exact implementation signature"
  }[node.node_kind] || node.node_kind);

  const metricCell = (value, className = "") =>
    `<span class="metric-cell ${className}">${escapeHtml(value)}</span>`;

  function layerSummary(layers) {
    if (!layers || layers.length === 0) return "non-layer tail / prologue";
    if (layers.length === 1) return `layer ${layers[0]}`;
    const contiguous = layers.every((value, index) => index === 0 || value === layers[index - 1] + 1);
    if (contiguous) return `layers ${layers[0]}–${layers[layers.length - 1]}`;
    if (layers.length <= 7) return `layers ${layers.join(", ")}`;
    return `${layers.length} layers (${layers[0]}–${layers[layers.length - 1]})`;
  }

  function renderContexts(contexts) {
    return contexts.map((context) => `
      <a class="context-chip" href="${escapeHtml(context.source_tree_href)}">
        <b>${escapeHtml(context.operation_id)}</b>
        <span>${escapeHtml(context.title)}</span>
        <i>${context.launches.toLocaleString()} launches</i>
      </a>
    `).join("");
  }

  function leafBody(node) {
    const config = node.launch_configuration;
    return `
      <div class="leaf-body">
        <div class="signature-grid">
          <div><span>Provider</span><strong title="${escapeHtml(node.provider)}">${escapeHtml(node.provider)}</strong></div>
          <div><span>Grid</span><strong>${config.grid.join(" × ")}</strong></div>
          <div><span>Block</span><strong>${config.block.join(" × ")}</strong></div>
          <div><span>Registers / thread</span><strong>${config.registers_per_thread}</strong></div>
          <div><span>Dynamic shared</span><strong>${config.dynamic_shared_bytes.toLocaleString()} B</strong></div>
          <div><span>Layer scope</span><strong title="${escapeHtml(layerSummary(node.layers))}">${escapeHtml(layerSummary(node.layers))}</strong></div>
        </div>
        <div class="raw-symbol-block">
          <span>Exact demangled raw symbol · SHA-256 ${escapeHtml(node.raw_kernel_name_sha256.slice(0, 16))}…</span>
          <code>${escapeHtml(node.raw_kernel_name)}</code>
        </div>
        <div class="context-block">
          <span>Logical owners in the original execution tree · cross-references only</span>
          <div class="context-list">${renderContexts(node.semantic_contexts)}</div>
        </div>
      </div>
    `;
  }

  function searchText(node, path) {
    const contexts = (node.semantic_contexts || [])
      .map((context) => `${context.operation_id} ${context.title}`)
      .join(" ");
    return [
      ...path,
      node.title,
      node.description,
      node.provider,
      node.raw_kernel_name,
      contexts
    ].filter(Boolean).join(" ").toLowerCase();
  }

  function renderNode(node, depth, inheritedColor, path = []) {
    const color = node.color || inheritedColor || "slate";
    const metrics = node.metrics;
    const currentPath = [...path, node.title];
    const details = document.createElement("details");
    details.className = `tree-node ${node.node_kind === "implementation_signature" ? "signature-node" : "branch-node"}`;
    details.dataset.depth = String(depth);
    details.dataset.color = color;
    details.dataset.search = searchText(node, currentPath);
    details.id = node.node_kind === "broad_type" ? `type-${node.id}` : node.id;
    details.open = depth === 0;

    const summary = document.createElement("summary");
    summary.innerHTML = `
      <span class="tree-summary-row">
        <span class="node-title-block">
          <span class="node-kicker">${escapeHtml(depthLabel(node))}</span>
          <span class="node-title" title="${escapeHtml(node.title)}">${escapeHtml(node.title)}</span>
          <span class="node-description" title="${escapeHtml(node.description || "")}">${escapeHtml(node.description || "")}</span>
        </span>
        ${metricCell(metrics.launches.toLocaleString())}
        ${metricCell(`${formatMs(metrics.summed_residency_ms)} ms`, "primary")}
        ${metricCell(`${metrics.residency_share_pct.toFixed(2)}%`)}
        ${metricCell(`${formatMs(metrics.active_union_ms)} ms`)}
        ${metricCell(`${formatMs(metrics.incremental_union_ms)} ms`)}
      </span>
    `;
    details.appendChild(summary);

    if (node.node_kind === "implementation_signature") {
      details.insertAdjacentHTML("beforeend", leafBody(node));
    } else {
      const children = document.createElement("div");
      children.className = "tree-children";
      node.children.forEach((child) => children.appendChild(renderNode(child, depth + 1, color, currentPath)));
      details.appendChild(children);
    }
    return details;
  }

  report.tree.children.forEach((node) => treeRoot.appendChild(renderNode(node, 0, node.color)));

  function setExpansion(mode) {
    treeRoot.querySelectorAll("details.tree-node").forEach((details) => {
      const depth = Number(details.dataset.depth);
      details.open = mode === "all" || (mode === "broad" && depth === 0);
    });
  }

  document.getElementById("open-broad").addEventListener("click", () => setExpansion("broad"));
  document.getElementById("open-all").addEventListener("click", () => setExpansion("all"));
  document.getElementById("close-all").addEventListener("click", () => setExpansion("none"));

  function applyFilter() {
    const query = search.value.trim().toLowerCase();
    const leaves = Array.from(treeRoot.querySelectorAll("details.signature-node"));
    let visibleLeaves = 0;
    leaves.forEach((leaf) => {
      const visible = !query || leaf.dataset.search.includes(query);
      leaf.hidden = !visible;
      if (visible) visibleLeaves += 1;
    });

    const branches = Array.from(treeRoot.querySelectorAll("details.branch-node"))
      .sort((left, right) => Number(right.dataset.depth) - Number(left.dataset.depth));
    branches.forEach((branch) => {
      const hasVisibleLeaf = Array.from(branch.querySelectorAll("details.signature-node"))
        .some((leaf) => !leaf.hidden);
      branch.hidden = !hasVisibleLeaf;
      if (query && hasVisibleLeaf) branch.open = true;
    });

    filterStatus.textContent = query
      ? `${visibleLeaves} of ${leaves.length} implementation signatures match`
      : `${leaves.length} implementation signatures · ${report.inventory.raw_symbol_count} raw symbols`;

    let empty = treeRoot.querySelector(".empty-search");
    if (visibleLeaves === 0 && !empty) {
      empty = document.createElement("p");
      empty.className = "empty-search";
      empty.textContent = "No exact implementation signature matches this filter.";
      treeRoot.appendChild(empty);
    } else if (visibleLeaves > 0 && empty) {
      empty.remove();
    }
  }

  search.addEventListener("input", applyFilter);

  function initializeContentsTracking() {
    const links = Array.from(document.querySelectorAll(".toc-link"));
    const sections = links
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${visible.target.id}`);
      });
    }, { rootMargin: "-12% 0px -70% 0px", threshold: [0, 0.05, 0.2] });
    sections.forEach((section) => observer.observe(section));
  }

  function revealHashTarget() {
    if (!window.location.hash) return;
    const target = document.querySelector(window.location.hash);
    if (!target) return;
    let current = target;
    while (current && current !== treeRoot) {
      if (current.tagName === "DETAILS") current.open = true;
      current = current.parentElement;
    }
  }

  initializeContentsTracking();
  revealHashTarget();
  window.addEventListener("hashchange", revealHashTarget);
})();
