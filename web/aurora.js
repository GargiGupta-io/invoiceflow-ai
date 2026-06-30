const auroraCanvas = document.getElementById("aurora-canvas");
const auroraHero = document.querySelector(".hero");

if (auroraCanvas && auroraHero) {
  const ctx = auroraCanvas.getContext("2d");
  const pointer = { x: 0.5, y: 0.55, active: false };
  let width = 0;
  let height = 0;
  let dpr = 1;
  let animationFrame = 0;

  const resizeAurora = () => {
    const rect = auroraHero.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(1, Math.floor(rect.height));
    auroraCanvas.width = Math.floor(width * dpr);
    auroraCanvas.height = Math.floor(height * dpr);
    auroraCanvas.style.width = `${width}px`;
    auroraCanvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  const updatePointer = (event) => {
    const rect = auroraHero.getBoundingClientRect();
    pointer.x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    pointer.y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    pointer.active = true;
  };

  const resetPointer = () => {
    pointer.active = false;
  };

  const drawWave = (time) => {
    ctx.clearRect(0, 0, width, height);

    const baseY = height * 0.28;
    const amplitude = Math.max(20, height * 0.032);
    const cursorPull = pointer.active ? (pointer.y - 0.28) * height * 0.12 : 0;
    const highlightX = pointer.x * width;

    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    for (let layer = 0; layer < 3; layer += 1) {
      const lineOffset = (layer - 1) * 10;
      const blur = layer === 0 ? 20 : layer === 1 ? 10 : 3;
      const alpha = layer === 0 ? 0.26 : layer === 1 ? 0.42 : 0.9;
      ctx.beginPath();
      for (let x = -20; x <= width + 20; x += 8) {
        const distance = Math.abs(x - highlightX) / Math.max(width, 1);
        const lift = pointer.active ? Math.max(0, 1 - distance * 4.2) * cursorPull : 0;
        const y =
          baseY +
          lineOffset +
          Math.sin(x * 0.008 + time * 0.0011 + layer * 0.7) * amplitude +
          Math.sin(x * 0.017 - time * 0.0009) * amplitude * 0.32 +
          lift;
        if (x === -20) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      gradient.addColorStop(0, `rgba(95, 143, 124, 0)`);
      gradient.addColorStop(0.18, `rgba(95, 143, 124, ${alpha})`);
      gradient.addColorStop(Math.max(0.22, pointer.x - 0.08), `rgba(247, 247, 229, ${Math.min(1, alpha + 0.18)})`);
      gradient.addColorStop(Math.min(0.78, pointer.x + 0.08), `rgba(247, 247, 229, ${Math.min(1, alpha + 0.18)})`);
      gradient.addColorStop(0.72, `rgba(222, 184, 124, ${alpha})`);
      gradient.addColorStop(1, `rgba(222, 184, 124, 0)`);

      ctx.strokeStyle = gradient;
      ctx.lineWidth = layer === 2 ? 7 : 22 + layer * 12;
      ctx.lineCap = "round";
      ctx.shadowColor = pointer.active ? "rgba(247, 247, 229, 0.78)" : "rgba(247, 247, 229, 0.52)";
      ctx.shadowBlur = blur;
      ctx.stroke();
    }

    ctx.restore();
    animationFrame = requestAnimationFrame(drawWave);
  };

  resizeAurora();
  window.addEventListener("resize", resizeAurora, { passive: true });
  auroraHero.addEventListener("pointermove", updatePointer);
  auroraHero.addEventListener("pointerleave", resetPointer);
  animationFrame = requestAnimationFrame(drawWave);

  window.addEventListener("beforeunload", () => {
    cancelAnimationFrame(animationFrame);
  });
}
