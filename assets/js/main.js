// HYMN project page: copy buttons, site-map tooltips and layer toggles.
// The page is fully readable without this script.
(() => {
  // Copy buttons on code blocks
  document.querySelectorAll("pre[data-copy]").forEach((pre) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText.trim());
        btn.textContent = "Copied";
      } catch {
        btn.textContent = "Select and copy";
      }
      setTimeout(() => { btn.textContent = "Copy"; }, 1600);
    });
    pre.parentElement.insertBefore(btn, pre);
  });

  const wrap = document.querySelector(".map-wrap");
  const svg = wrap && wrap.querySelector("svg");
  if (!svg) return;
  const tip = wrap.querySelector(".map-tip");

  // Native <title> tooltips remain for no-JS readers; replace them here.
  svg.querySelectorAll("[data-tip] > title").forEach((t) => t.remove());

  let active = null;
  const place = (x, y) => {
    const box = wrap.getBoundingClientRect();
    let left = x - box.left + 12;
    let top = y - box.top + 12;
    if (left + tip.offsetWidth > box.width - 4) left = x - box.left - tip.offsetWidth - 12;
    if (top + tip.offsetHeight > box.height - 4) top = y - box.top - tip.offsetHeight - 12;
    tip.style.left = `${Math.max(4, left)}px`;
    tip.style.top = `${Math.max(4, top)}px`;
  };
  const show = (el, e) => {
    if (active && active !== el) active.classList.remove("is-active");
    active = el;
    el.classList.add("is-active");
    tip.textContent = el.dataset.tip;
    tip.hidden = false;
    place(e.clientX, e.clientY);
  };
  const hide = () => {
    if (active) active.classList.remove("is-active");
    active = null;
    tip.hidden = true;
  };

  svg.addEventListener("pointermove", (e) => {
    const el = e.target.closest("[data-tip]");
    if (el) show(el, e);
    else if (e.pointerType === "mouse") hide();
  });
  svg.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hide(); });
  svg.addEventListener("pointerdown", (e) => {
    const el = e.target.closest("[data-tip]");
    if (el) show(el, e); else hide();
  });

  // Layer toggles for anchor technologies
  const layers = document.querySelector(".layers");
  if (layers) {
    layers.hidden = false;
    layers.querySelectorAll("button[data-layer]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const on = btn.getAttribute("aria-pressed") !== "true";
        btn.setAttribute("aria-pressed", String(on));
        wrap.classList.toggle(`hide-${btn.dataset.layer}`, !on);
        hide();
      });
    });
  }
})();
