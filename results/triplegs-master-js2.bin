document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  const button = document.querySelector(".toggle");
  const menu = document.querySelector(".menu");

  if (button && menu) {
    button.addEventListener("click", () => {
      menu.classList.toggle("show");
      button.classList.toggle("change");
      const isExpanded = menu.classList.contains("show");
      menu.setAttribute("aria-hidden", !isExpanded);
    });

    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        menu.classList.remove("show");
        button.classList.remove("change");
        menu.setAttribute("aria-hidden", "true");
      });
    });
  }

  const TOTAL_FRAMES = 48;
  const FRAME_DIR = "frames/";

  function pad3(n) {
    return String(n).padStart(3, "0");
  }

  function frameSrc(n) {
    return `${FRAME_DIR}frame-${pad3(n)}.webp`;
  }

  const stage = document.querySelector(".sequence-sticky");
  const canvas = document.getElementById("seq-canvas");
  if (!canvas || !stage) return;

  const ctx = canvas.getContext("2d");
  const loaderEl = document.getElementById("loader");
  const loaderFill = document.getElementById("loader-fill");
  const loaderText = document.getElementById("loader-text");
  const counterEl = document.getElementById("frame-counter");
  const railFill = document.getElementById("rail-fill");
  const captionEls = Array.from(document.querySelectorAll(".caption"));

  const images = new Array(TOTAL_FRAMES);
  let loadedOk = 0;
  let loadedFail = 0;
  let highestContiguous = -1;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  const state = { frame: 0 };
  let lastDrawnIndex = -1;

  function sizeCanvas() {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    lastDrawnIndex = -1;
    render(true);
  }

  function fillStageColor(w, h) {
    ctx.fillStyle = "#14100c";
    ctx.fillRect(0, 0, w, h);
  }

  function drawCover(img) {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight);
    const dw = img.naturalWidth * scale;
    const dh = img.naturalHeight * scale;
    const dx = (w - dw) / 2;
    const dy = (h - dh) / 2;

    fillStageColor(w, h);
    ctx.drawImage(img, dx, dy, dw, dh);
  }

  function updateUI(idx) {
    if (counterEl) {
      counterEl.textContent = `${pad3(idx + 1)} / ${TOTAL_FRAMES}`;
    }
    const pct = idx / (TOTAL_FRAMES - 1);
    if (railFill) {
      railFill.style.transform = `scaleX(${pct})`;
    }

    captionEls.forEach((el) => {
      const rangeAttr = el.getAttribute("data-range");
      if (!rangeAttr) return;
      const range = rangeAttr.split(",").map(Number);
      const on = pct >= range[0] && pct <= range[1];
      el.classList.toggle("is-visible", on);
    });
  }

  function render(force) {
    const target = Math.round(state.frame);
    const idx =
      target <= highestContiguous ? target : Math.max(highestContiguous, 0);

    if (!force && idx === lastDrawnIndex) return;
    lastDrawnIndex = idx;

    const img = images[idx];
    if (img && img.complete && img.naturalWidth) {
      drawCover(img);
    } else {
      fillStageColor(stage.clientWidth, stage.clientHeight);
    }
    updateUI(idx);
  }

  function recomputeHighestContiguous() {
    let h = -1;
    for (let i = 0; i < TOTAL_FRAMES; i++) {
      const img = images[i];
      if (img && img.complete && img.naturalWidth) {
        h = i;
      } else {
        break;
      }
    }
    highestContiguous = h;
  }

  function updateLoaderUI() {
    const done = loadedOk + loadedFail;
    const frac = done / TOTAL_FRAMES;
    if (loaderFill) loaderFill.style.transform = `scaleX(${frac})`;
    if (loaderText)
      loaderText.textContent = `Loading sequence — ${Math.round(frac * 100)}%`;

    if (done >= TOTAL_FRAMES) {
      if (loadedFail > TOTAL_FRAMES * 0.15) {
        if (loaderEl) loaderEl.classList.add("is-error");
        if (loaderText)
          loaderText.textContent =
            "Some frames didn't load — showing what's available.";
        setTimeout(() => {
          if (loaderEl) loaderEl.classList.add("is-hidden");
        }, 1600);
      } else {
        if (loaderEl) loaderEl.classList.add("is-hidden");
      }
      if (window.ScrollTrigger) ScrollTrigger.refresh();
    }
  }

  function preload() {
    for (let i = 0; i < TOTAL_FRAMES; i++) {
      const img = new Image();
      img.decoding = "async";
      img.onload = () => {
        loadedOk++;
        recomputeHighestContiguous();
        updateLoaderUI();
        if (i === 0) render(true);
      };
      img.onerror = () => {
        loadedFail++;
        updateLoaderUI();
      };
      img.src = frameSrc(i + 1);
      images[i] = img;
    }
  }

  function initScroll() {
    const prefersReduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReduced || !window.gsap || !window.ScrollTrigger) {
      state.frame = TOTAL_FRAMES - 1;
      render(true);
      captionEls.forEach((el) => el.classList.remove("is-visible"));
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    ScrollTrigger.create({
      trigger: "#sequence",
      start: "top top",
      end: `+=${TOTAL_FRAMES * 16}`,
      pin: ".sequence-sticky",
      scrub: 0.4,
      anticipatePin: 1,
      onUpdate: (self) => {
        state.frame = self.progress * (TOTAL_FRAMES - 1);
        render();
      },
    });
  }

  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  window.addEventListener(
    "resize",
    debounce(() => {
      sizeCanvas();
      if (window.ScrollTrigger) ScrollTrigger.refresh();
    }, 150),
  );

  sizeCanvas();
  preload();
  initScroll();
});

// aboutSection

document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  const aboutSection = document.getElementById("about");
  if (!aboutSection || !window.gsap || !window.ScrollTrigger) return;

  const words = aboutSection.querySelectorAll(".about-word");
  const desc = aboutSection.querySelector(".about-desc");

  const prefersReduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (prefersReduced) {
    gsap.set(words, { opacity: 1, y: 0 });
    gsap.set(desc, { opacity: 1, y: 0 });
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: aboutSection,
      start: "top 65%",
      toggleActions: "play none none reverse",
    },
  });

  tl.to(words, {
    yPercent: 140,
    opacity: 1,
    duration: 0.7,
    ease: "back.out(1.6)",
    stagger: 0.16,
  }).to(
    desc,
    {
      y: 0,
      opacity: 1,
      duration: 0.6,
      ease: "power2.out",
    },
    "-=0.15"
  );
});