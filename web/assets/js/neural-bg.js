/* Animated neural-network backdrop. Vanilla canvas, no dependencies.
   Nodes drift slowly; edges fade in as nodes approach, so the field reads as a
   living graph rather than decoration. Respects prefers-reduced-motion and
   throttles node count on small screens. */
(function () {
  "use strict";
  const canvas = document.getElementById("neural");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let w, h, nodes, raf;
  const LINK = 150; // px within which two nodes draw an edge

  function resize() {
    w = canvas.width = window.innerWidth * devicePixelRatio;
    h = canvas.height = window.innerHeight * devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    const target = Math.min(90, Math.floor((window.innerWidth * window.innerHeight) / 16000));
    nodes = Array.from({ length: target }, spawn);
  }

  function spawn() {
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.25 * devicePixelRatio,
      vy: (Math.random() - 0.5) * 0.25 * devicePixelRatio,
      r: (Math.random() * 1.6 + 0.6) * devicePixelRatio,
    };
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    const link = LINK * devicePixelRatio;

    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      a.x += a.vx; a.y += a.vy;
      if (a.x < 0 || a.x > w) a.vx *= -1;
      if (a.y < 0 || a.y > h) a.vy *= -1;

      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d = Math.hypot(dx, dy);
        if (d < link) {
          const o = (1 - d / link) * 0.5;
          ctx.strokeStyle = "rgba(46, 230, 198, " + o.toFixed(3) + ")";
          ctx.lineWidth = 0.6 * devicePixelRatio;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    for (const n of nodes) {
      ctx.beginPath();
      ctx.fillStyle = "rgba(120, 220, 240, 0.85)";
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    }

    raf = requestAnimationFrame(frame);
  }

  function start() {
    resize();
    if (reduce) { frame(); cancelAnimationFrame(raf); return; } // single static paint
    frame();
  }

  window.addEventListener("resize", () => { cancelAnimationFrame(raf); start(); });
  start();
})();
