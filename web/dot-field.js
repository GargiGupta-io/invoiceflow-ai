const dotFieldCanvas = document.getElementById("dot-field-canvas");

if (dotFieldCanvas) {
  const ctx = dotFieldCanvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const pointer = {
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
    targetX: window.innerWidth / 2,
    targetY: window.innerHeight / 2,
    active: false,
    lastMove: 0
  };

  let width = 0;
  let height = 0;
  let dpr = 1;
  let dots = [];
  let frameId = 0;

  const buildDots = () => {
    const spacing = width < 760 ? 34 : 30;
    const columns = Math.ceil(width / spacing) + 2;
    const rows = Math.ceil(height / spacing) + 2;
    dots = [];

    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        const seed = Math.sin(column * 18.73 + row * 43.19) * 10000;
        const jitterX = (seed - Math.floor(seed) - 0.5) * spacing * 0.18;
        const jitterY = (Math.sin(seed) - Math.floor(Math.sin(seed)) - 0.5) * spacing * 0.18;
        dots.push({
          x: column * spacing - spacing + jitterX,
          y: row * spacing - spacing + jitterY,
          seed
        });
      }
    }
  };

  const resizeDotField = () => {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    dotFieldCanvas.width = Math.floor(width * dpr);
    dotFieldCanvas.height = Math.floor(height * dpr);
    dotFieldCanvas.style.width = `${width}px`;
    dotFieldCanvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildDots();
  };

  const updatePointer = (event) => {
    pointer.targetX = event.clientX;
    pointer.targetY = event.clientY;
    pointer.active = true;
    pointer.lastMove = performance.now();
  };

  const drawDotField = (time) => {
    ctx.clearRect(0, 0, width, height);

    pointer.x += (pointer.targetX - pointer.x) * 0.16;
    pointer.y += (pointer.targetY - pointer.y) * 0.16;

    if (performance.now() - pointer.lastMove > 1800) {
      pointer.active = false;
    }

    const influenceRadius = Math.min(width, height) < 760 ? 110 : 150;
    const baseAlpha = 0.22;
    const idlePulse = reduceMotion ? 0 : Math.sin(time * 0.001) * 0.12;

    for (const dot of dots) {
      const dx = dot.x - pointer.x;
      const dy = dot.y - pointer.y;
      const distance = Math.hypot(dx, dy);
      const influence = pointer.active ? Math.max(0, 1 - distance / influenceRadius) : 0;
      const directionX = distance ? dx / distance : 0;
      const directionY = distance ? dy / distance : 0;
      const displacement = influence * 13;
      const shimmer = reduceMotion ? 0 : Math.sin(time * 0.0014 + dot.seed) * 0.18;
      const radius = 1.05 + influence * 1.7 + Math.max(0, shimmer + idlePulse) * 0.18;
      const alpha = baseAlpha + influence * 0.48 + Math.max(0, shimmer) * 0.05;
      const x = dot.x + directionX * displacement;
      const y = dot.y + directionY * displacement;

      ctx.beginPath();
      ctx.fillStyle = influence > 0.03
        ? `rgba(95, 146, 127, ${Math.min(0.78, alpha)})`
        : `rgba(31, 39, 33, ${Math.min(0.34, alpha)})`;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    if (pointer.active) {
      const glow = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, influenceRadius * 1.08);
      glow.addColorStop(0, "rgba(255, 251, 241, 0.18)");
      glow.addColorStop(0.45, "rgba(112, 166, 139, 0.08)");
      glow.addColorStop(1, "rgba(112, 166, 139, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(pointer.x - influenceRadius, pointer.y - influenceRadius, influenceRadius * 2, influenceRadius * 2);
    }

    frameId = requestAnimationFrame(drawDotField);
  };

  resizeDotField();
  window.addEventListener("resize", resizeDotField, { passive: true });
  window.addEventListener("pointermove", updatePointer, { passive: true });
  window.addEventListener("pointerleave", () => {
    pointer.active = false;
  });
  frameId = requestAnimationFrame(drawDotField);

  window.addEventListener("beforeunload", () => {
    cancelAnimationFrame(frameId);
  });
}
