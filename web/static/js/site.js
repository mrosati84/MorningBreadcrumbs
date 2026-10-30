/* Morning Breadcrumbs – progressive enhancements.
 *
 * The site works without this file; each module below only adds motion or
 * convenience on top of server-rendered HTML.
 */
(() => {
  "use strict";

  const root = document.documentElement;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* Reveal on scroll ------------------------------------------------- */

  // <head> adds .reveal-on (which hides [data-reveal]) only when
  // IntersectionObserver exists; here each element is shown once it scrolls in.
  function initReveal() {
    if (!root.classList.contains("reveal-on")) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
    );
    document.querySelectorAll("[data-reveal]").forEach((el) => observer.observe(el));
  }

  /* Sky glow following the pointer --------------------------------- */

  // Eases the glow centre toward the pointer. The animation loop only runs
  // while the glow is still moving, so an idle page does no per-frame work.
  function initSky() {
    if (reducedMotion.matches) return;

    const home = { x: 86, y: 4 };
    const pull = 0.45; // how far the glow follows the pointer (0–1)
    const easing = 0.05; // fraction of the remaining distance covered per frame
    const current = { ...home };
    const target = { ...home };
    let frame = 0;

    const step = () => {
      current.x += (target.x - current.x) * easing;
      current.y += (target.y - current.y) * easing;
      root.style.setProperty("--sky-x", `${current.x.toFixed(2)}%`);
      root.style.setProperty("--sky-y", `${current.y.toFixed(2)}%`);

      const settled =
        Math.abs(target.x - current.x) < 0.05 && Math.abs(target.y - current.y) < 0.05;
      frame = settled ? 0 : requestAnimationFrame(step);
    };

    const aim = (x, y) => {
      target.x = x;
      target.y = y;
      if (!frame) frame = requestAnimationFrame(step);
    };

    window.addEventListener(
      "pointermove",
      (event) => {
        if (event.pointerType !== "mouse") return;
        const px = (event.clientX / window.innerWidth) * 100;
        const py = (event.clientY / window.innerHeight) * 100;
        aim(home.x + (px - home.x) * pull, home.y + (py - home.y) * pull);
      },
      { passive: true },
    );
    document.addEventListener("mouseleave", () => aim(home.x, home.y));
  }

  /* Stacking sections ------------------------------------------------ */

  // Each section sticks once its bottom reaches the bottom of the viewport
  // (or just below the category bar when it is shorter than the screen),
  // so the next section slides over it like a card.
  function initStack() {
    const stack = document.querySelector("[data-stack]");
    const items = stack ? [...stack.querySelectorAll("[data-stack-item]")] : [];
    if (!items.length) return;

    const nav = stack.querySelector("[data-tabs]");
    // Sections stick a little under the category bar so their thick top rule
    // tucks behind it instead of doubling up with the bar's own rule.
    const TUCK = 5;
    let queued = false;

    const measure = () => {
      queued = false;
      const navHeight = nav ? nav.offsetHeight : 0;
      const viewport = window.innerHeight;
      for (const item of items) {
        const top = Math.round(Math.min(navHeight - TUCK, viewport - item.offsetHeight));
        item.style.setProperty("--stack-top", `${top}px`);
      }
      root.classList.add("stack-on");
    };

    const schedule = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("resize", schedule);
    // Heights change as images and web fonts load.
    const observer = new ResizeObserver(schedule);
    items.forEach((item) => observer.observe(item));
    if (nav) observer.observe(nav);
  }

  /* Category bar: drag to scroll ------------------------------------ */

  // On narrow screens the tabs scroll sideways. Touch scrolls natively; with a
  // mouse the track can be dragged, and a drag never counts as a click.
  function initTabs() {
    const track = document.querySelector("[data-tabs-track]");
    if (!track) return;

    const active = track.querySelector(".tab.is-active");
    if (active && track.scrollWidth > track.clientWidth) {
      track.scrollLeft = active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2;
    }

    let pointerId = null;
    let startX = 0;
    let startScroll = 0;
    let dragging = false;

    const suppressClick = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };

    track.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "touch" || track.scrollWidth <= track.clientWidth) return;
      pointerId = event.pointerId;
      startX = event.clientX;
      startScroll = track.scrollLeft;
      dragging = false;
    });

    track.addEventListener("pointermove", (event) => {
      if (event.pointerId !== pointerId) return;
      const dx = event.clientX - startX;
      if (!dragging && Math.abs(dx) > 4) {
        dragging = true;
        track.classList.add("is-dragging");
        track.setPointerCapture(pointerId);
      }
      if (dragging) {
        track.scrollLeft = startScroll - dx;
        event.preventDefault();
      }
    });

    const end = (event) => {
      if (event.pointerId !== pointerId) return;
      pointerId = null;
      if (!dragging) return;
      dragging = false;
      track.classList.remove("is-dragging");
      // The click that follows pointerup must not follow the tab's link.
      track.addEventListener("click", suppressClick, { capture: true, once: true });
      setTimeout(() => track.removeEventListener("click", suppressClick, { capture: true }), 0);
    };

    track.addEventListener("pointerup", end);
    track.addEventListener("pointercancel", end);
  }

  /* Search box ------------------------------------------------------- */

  function initSearch() {
    const form = document.querySelector("[data-search]");
    if (!form) return;

    const input = form.querySelector("input[type=search]");
    const close = form.querySelector("[data-search-close]");
    // Set on the results page: closing the search leaves the results.
    const exitUrl = form.dataset.searchExit;

    const sync = () => form.classList.toggle("is-filled", input.value.trim() !== "");
    input.addEventListener("input", sync);

    form.addEventListener("submit", (event) => {
      if (input.value.trim() === "") {
        event.preventDefault();
        input.blur();
      }
    });

    // pointerdown + preventDefault keeps focus in the input, so the button
    // does not disappear (via :focus-within) before the click lands.
    close.addEventListener("pointerdown", (event) => event.preventDefault());
    close.addEventListener("click", () => {
      if (exitUrl) {
        window.location.assign(exitUrl);
        return;
      }
      input.value = "";
      sync();
      input.blur();
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close.click();
    });
  }

  /* Issue archive dialog -------------------------------------------- */

  function initArchive() {
    const dialog = document.querySelector("[data-archive]");
    if (!dialog) return;

    document.querySelectorAll("[data-archive-open]").forEach((button) => {
      button.addEventListener("click", () => {
        dialog.showModal();
        // Focus the dialog itself rather than its first button, so opening
        // with a click shows no focus ring; Tab still moves through the issues.
        dialog.focus();
      });
    });
    dialog.querySelectorAll("[data-archive-close]").forEach((button) => {
      button.addEventListener("click", () => dialog.close());
    });
  }

  initReveal();
  initSky();
  initStack();
  initTabs();
  initSearch();
  initArchive();
})();
