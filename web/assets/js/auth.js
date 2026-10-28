/* Login controller. Tries the live backend first; if nothing answers, drops to
   a self-contained demo so the console still opens on a static host. The demo
   path validates the published demo credentials client-side only. It grants no
   real authority, it just unlocks the in-browser mirror engine. */
(function () {
  "use strict";
  const form = document.getElementById("login-form");
  if (!form) return;

  const statusEl = document.getElementById("status");
  const btn = document.getElementById("submit");
  const DEMO = { user: "shomer", pass: "emet-2026" };

  function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  function store(token, mode, subject) {
    sessionStorage.setItem("shomer.token", token);
    sessionStorage.setItem("shomer.mode", mode);
    sessionStorage.setItem("shomer.subject", subject);
  }

  async function tryLive(username, password) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 2500);
    try {
      const res = await fetch("api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        signal: ctrl.signal,
      });
      clearTimeout(t);
      if (res.status === 401) return { outcome: "denied" };
      if (!res.ok) return { outcome: "unreachable" };
      const data = await res.json();
      return { outcome: "ok", token: data.token, subject: data.subject };
    } catch (_e) {
      clearTimeout(t);
      return { outcome: "unreachable" };
    }
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    if (!username || !password) { setStatus("Enter both fields.", "err"); return; }

    btn.disabled = true;
    setStatus("Authenticating\u2026");

    const live = await tryLive(username, password);
    if (live.outcome === "ok") {
      store(live.token, "live", live.subject);
      setStatus("Welcome. Opening the console\u2026", "ok");
      location.href = "dashboard.html";
      return;
    }
    if (live.outcome === "denied") {
      setStatus("Invalid credentials.", "err");
      btn.disabled = false;
      return;
    }
    // Unreachable backend: fall back to the in-browser demo.
    if (username === DEMO.user && password === DEMO.pass) {
      store("demo.local", "demo", username);
      setStatus("No backend reachable \u2014 opening offline demo\u2026", "ok");
      location.href = "dashboard.html";
      return;
    }
    setStatus("No backend reachable. Use the demo credentials to continue offline.", "err");
    btn.disabled = false;
  });
})();
