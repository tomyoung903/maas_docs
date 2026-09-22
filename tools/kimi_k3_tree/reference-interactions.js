(() => {
  const tree = document.querySelector(".flow-tree");
  if (!tree) return;

  const columnLabels = {
    io: "Tensor input to tensor output",
    state: "Logical parameter state",
    flops: "100K prefill FLOPs",
  };

  document.querySelectorAll(".column-toggle[data-column]").forEach((button) => {
    const column = button.dataset.column;
    const label = columnLabels[column];
    if (!label) return;

    const setVisible = (visible) => {
      tree.classList.toggle(`hide-${column}`, !visible);
      button.setAttribute("aria-pressed", String(visible));
      button.title = `${visible ? "Hide" : "Show"} ${label} column`;
    };

    setVisible(button.getAttribute("aria-pressed") !== "false");
    button.addEventListener("click", () => {
      setVisible(button.getAttribute("aria-pressed") !== "true");
    });
  });

  const setExpanded = (step, expanded) => {
    const children = step.querySelector(":scope > .flow-children");
    const button = step.querySelector(":scope > .flow-row .flow-toggle");
    if (!children || !button) return;

    step.classList.toggle("is-collapsed", !expanded);
    children.hidden = !expanded;
    button.setAttribute("aria-expanded", String(expanded));
    const action = expanded ? "Collapse" : "Expand";
    const stepId = button.dataset.step;
    button.setAttribute("aria-label", `${action} child modules under step ${stepId}`);
    button.title = `${action} child modules`;
  };

  tree.addEventListener("click", (event) => {
    const row = event.target.closest(".flow-row");
    const step = row?.parentElement;
    if (!step?.classList.contains("has-children")) return;
    if (window.getSelection()?.toString()) return;
    setExpanded(step, step.classList.contains("is-collapsed"));
  });
})();