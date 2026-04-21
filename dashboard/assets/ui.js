/* ---------------------------------------------------------------------------
   ui.js — Tab switching between views.
--------------------------------------------------------------------------- */

function initTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  const panels = document.querySelectorAll(".panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.view;

      // Toggle tabs
      tabs.forEach((t) => {
        const isActive = t === tab;
        t.classList.toggle("view-tab--active", isActive);
        t.setAttribute("aria-selected", isActive ? "true" : "false");
      });

      // Toggle panels
      panels.forEach((p) => {
        const isActive = p.dataset.panel === target;
        if (isActive) {
          p.removeAttribute("hidden");
        } else {
          p.setAttribute("hidden", "");
        }
      });

      // Resize charts when their panel becomes visible (Chart.js needs it
      // because it cached a size of 0 while the panel was hidden).
      window.dispatchEvent(new Event("resize"));
    });
  });
}
