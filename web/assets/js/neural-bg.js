/* Animated neural-network backdrop. Vanilla canvas, no dependencies.
   Nodes drift slowly and link when close; near the cursor they brighten and
   connect to the pointer, so the field feels alive and reactive rather than
   decorative. Respects prefers-reduced-motion and throttles on small screens. */
(function () {
  "use strict";
  const canvas = document.getElementById("neural");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let w, h, nodes, raf;
  const LINK = 150;          // px within which two nodes draw an edge
  const CURSOR = 220;        // px within which a node reacts to the pointer
  const mouse = { x: -9999, y: -9999, on: false };

  function resize() {
    w = canvas.width = window.innerWidth * devicePixelRatio;
    h = canvas.height = window.innerHeight * devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    const target = Math.min(100, Math.floor((window.innerWidth * window.innerHeight) / 14000));
    nodes = Array.from({ length: target }, spawn);
  }

  function spawn() {
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.28 * devicePixelRatio,
      vy: (Math.random() - 0.5) * 0.28 * devicePixelRatio,
      r: (Math.random() * 1.7 + 0.6) * devicePixelRatio,
    };
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    const link = LINK * devicePixelRatio;
    const reach = CURSOR * devicePixelRatio;

    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      a.x += a.vx; a.y += a.vy;
      if (a.x < 0 || a.x > w) a.vx *= -1;
      if (a.y < 0 || a.y > h) a.vy *= -1;

      // gentle drift toward the pointer when it is near
      if (mouse.on) {
        const mdx = mouse.x - a.x, mdy = mouse.y - a.y;
        const md = Math.hypot(mdx, mdy);
        if (md < reach && md > 1) {
          const pull = (1 - md / reach) * 0.06;
          a.x += (mdx / md) * pull * devicePixelRatio;
          a.y += (mdy / md) * pull * devicePixelRatio;
        }
      }

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

    // cursor-reactive layer: lines to the pointer + brighter nodes
    for (const n of nodes) {
      let glow = 0;
      if (mouse.on) {
        const dx = mouse.x - n.x, dy = mouse.y - n.y;
        const d = Math.hypot(dx, dy);
        if (d < reach) {
          glow = 1 - d / reach;
          ctx.strokeStyle = "rgba(56, 189, 248, " + (glow * 0.6).toFixed(3) + ")";
          ctx.lineWidth = 0.8 * devicePixelRatio;
          ctx.beginPath();
          ctx.moveTo(n.x, n.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }
      }
      ctx.beginPath();
      ctx.fillStyle = glow > 0
        ? "rgba(160, 240, 255, " + (0.7 + glow * 0.3).toFixed(3) + ")"
        : "rgba(120, 220, 240, 0.85)";
      ctx.arc(n.x, n.y, n.r * (1 + glow * 1.4), 0, Math.PI * 2);
      ctx.fill();
    }

    raf = requestAnimationFrame(frame);
  }

  function onMove(e) {
    const t = e.touches ? e.touches[0] : e;
    mouse.x = t.clientX * devicePixelRatio;
    mouse.y = t.clientY * devicePixelRatio;
    mouse.on = true;
  }
  function onLeave() { mouse.on = false; mouse.x = mouse.y = -9999; }

  function start() {
    resize();
    if (reduce) { frame(); cancelAnimationFrame(raf); return; }
    frame();
  }

  window.addEventListener("resize", () => { cancelAnimationFrame(raf); start(); });
  window.addEventListener("mousemove", onMove, { passive: true });
  window.addEventListener("touchmove", onMove, { passive: true });
  window.addEventListener("mouseout", onLeave);
  start();
})();
