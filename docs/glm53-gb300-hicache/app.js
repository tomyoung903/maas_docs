(() => {
  "use strict";

  const explorer = document.querySelector("[data-flow-explorer]");

  if (explorer) {
    const tabs = Array.from(explorer.querySelectorAll('[role="tab"]'));
    const panels = Array.from(explorer.querySelectorAll('[role="tabpanel"]'));
    const nodes = Array.from(explorer.querySelectorAll(".flow-node[data-modes]"));

    const activate = (mode, moveFocus = false) => {
      explorer.dataset.mode = mode;

      tabs.forEach((tab) => {
        const selected = tab.dataset.mode === mode;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
        if (selected && moveFocus) tab.focus();
      });

      panels.forEach((panel) => {
        panel.hidden = panel.dataset.panel !== mode;
      });

      nodes.forEach((node) => {
        const relevant = node.dataset.modes.split(/\s+/).includes(mode);
        node.classList.toggle("is-relevant", relevant);
        node.classList.toggle("is-dimmed", !relevant);
      });
    };

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activate(tab.dataset.mode));
      tab.addEventListener("keydown", (event) => {
        let nextIndex = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          nextIndex = (index + 1) % tabs.length;
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          nextIndex = (index - 1 + tabs.length) % tabs.length;
        } else if (event.key === "Home") {
          nextIndex = 0;
        } else if (event.key === "End") {
          nextIndex = tabs.length - 1;
        }

        if (nextIndex !== null) {
          event.preventDefault();
          activate(tabs[nextIndex].dataset.mode, true);
        }
      });
    });

    activate(explorer.dataset.mode || "read");
  }

  const railLinks = Array.from(document.querySelectorAll('.overview nav a[href^="#"]'));
  const sections = railLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length) {
    const byId = new Map(
      railLinks.map((link) => [link.getAttribute("href").slice(1), link])
    );

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (!visible.length) return;

        railLinks.forEach((link) => link.removeAttribute("aria-current"));
        const active = byId.get(visible[0].target.id);
        if (active) active.setAttribute("aria-current", "true");
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: 0 }
    );

    sections.forEach((section) => observer.observe(section));
  }
})();
