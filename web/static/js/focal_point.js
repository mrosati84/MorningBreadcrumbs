// Focal point picker for the Post admin (see web/widgets.py).
(() => {
  "use strict";

  const clamp = (value) => Math.min(100, Math.max(0, Math.round(value)));

  function init(root) {
    const form = root.closest("form");
    const xInput = form?.elements.namedItem(root.dataset.xField);
    const yInput = form?.elements.namedItem(root.dataset.yField);
    if (!xInput || !yInput) return;

    const row = root.parentElement;
    const fileInput = row.querySelector('input[type="file"]');
    const clearInput = row.querySelector('input[type="checkbox"][name$="-clear"]');
    const stage = root.querySelector(".focal__stage");
    const marker = root.querySelector(".focal__marker");
    const images = root.querySelectorAll("img");
    const savedSrc = root.dataset.src;
    const savedPoint = [xInput.value, yInput.value];
    let objectUrl = null;

    function set(x, y) {
      xInput.value = clamp(x);
      yInput.value = clamp(y);
      render();
    }

    function render() {
      const x = clamp(Number(xInput.value) || 0);
      const y = clamp(Number(yInput.value) || 0);
      marker.style.left = `${x}%`;
      marker.style.top = `${y}%`;
      stage.setAttribute("aria-valuetext", `${x}% from left, ${y}% from top`);
      images.forEach((img) => {
        img.style.objectPosition = `${x}% ${y}%`;
      });
    }

    function show(src) {
      root.hidden = !src || clearInput?.checked;
      if (src) images.forEach((img) => (img.src = src));
    }

    function pointTo(event) {
      const box = stage.getBoundingClientRect();
      if (!box.width || !box.height) return;
      set(
        ((event.clientX - box.left) / box.width) * 100,
        ((event.clientY - box.top) / box.height) * 100,
      );
    }

    // Capture keeps the drag going when the pointer leaves the image.
    let dragging = null;

    stage.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      dragging = event.pointerId;
      try {
        stage.setPointerCapture(event.pointerId);
      } catch {
        // Not an active pointer (e.g. a synthetic event): drag inside the image only.
      }
      stage.focus();
      pointTo(event);
    });

    stage.addEventListener("pointermove", (event) => {
      if (event.pointerId === dragging) pointTo(event);
    });

    const stop = (event) => {
      if (event.pointerId === dragging) dragging = null;
    };
    stage.addEventListener("pointerup", stop);
    stage.addEventListener("pointercancel", stop);

    stage.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 10 : 1;
      const moves = {
        ArrowLeft: [-step, 0],
        ArrowRight: [step, 0],
        ArrowUp: [0, -step],
        ArrowDown: [0, step],
      };
      const move = moves[event.key];
      if (!move) return;
      event.preventDefault();
      set(Number(xInput.value) + move[0], Number(yInput.value) + move[1]);
    });

    root.querySelector(".focal__reset").addEventListener("click", () => set(50, 50));

    // A new upload is previewed locally, so the point can be chosen before
    // saving; the old point belongs to the old image, so start from the center.
    fileInput?.addEventListener("change", () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = null;
      const file = fileInput.files?.[0];
      if (file && file.type.startsWith("image/")) {
        objectUrl = URL.createObjectURL(file);
        set(50, 50);
        show(objectUrl);
      } else {
        set(...savedPoint);
        show(savedSrc);
      }
    });

    clearInput?.addEventListener("change", () => show(objectUrl || savedSrc));

    render();
    show(savedSrc);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-focal]").forEach(init);
  });
})();
