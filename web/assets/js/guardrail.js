/* Client-side mirror of the deterministic engine.
   This is NOT the authoritative engine. The Python engine under src/ is, and
   it is the one the tests and the eval gate measure. This mirror exists so the
   console still works as a static page with no backend, running the exact same
   rule ids, weights and patterns in the browser. If the two ever drift, the
   Python side wins; docs/architecture.md says so. */
(function () {
  "use strict";

  const RULES = [
    { id: "IO-01", category: "instruction_override", weight: 5.0,
      rationale: "Tells the model to ignore or discard its prior instructions.",
      re: /\b(ignore|disregard|forget|override)\b[^.]{0,40}\b(previous|prior|above|earlier|all)\b[^.]{0,20}\b(instruction|instructions|prompt|prompts|rule|rules|context)\b/i },
    { id: "IO-02", category: "instruction_override", weight: 4.0,
      rationale: "Resets the conversation to erase the governing system prompt.",
      re: /\b(start over|begin again|reset)\b[^.]{0,30}\b(ignoring|without)\b[^.]{0,30}\b(instruction|rule|constraint)/i },
    { id: "RH-01", category: "role_hijack", weight: 3.5,
      rationale: "Reassigns the model's persona to escape its guardrails.",
      re: /\b(you are now|from now on,? you are|act as|pretend to be|roleplay as|behave like)\b/i },
    { id: "SE-01", category: "system_prompt_exfil", weight: 4.0,
      rationale: "Attempts to read back the hidden system prompt or instructions.",
      re: /\b(reveal|show|print|repeat|output|display|tell me)\b[^.]{0,30}\b(your|the)\b[^.]{0,20}\b(system prompt|instructions|rules|prompt|guidelines)\b/i },
    { id: "SE-02", category: "system_prompt_exfil", weight: 3.5,
      rationale: "The 'repeat the words above' exfiltration trick.",
      re: /\brepeat\b[^.]{0,20}\b(the )?(words|text|everything)\b[^.]{0,10}\babove\b/i },
    { id: "DS-01", category: "delimiter_spoof", weight: 4.5,
      rationale: "Injects fake chat-template markers to forge a system turn.",
      re: /(<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]|<<SYS>>|<<\/SYS>>)/ },
    { id: "DS-02", category: "delimiter_spoof", weight: 3.0,
      rationale: "Forges a role header (system:/assistant:) to hijack the turn.",
      re: /(^|\n)\s*(###\s*)?(system|assistant|developer)\s*:/i },
    { id: "EE-01", category: "encoding_evasion", weight: 3.0,
      rationale: "A long base64 blob used to smuggle a payload past text filters.",
      re: /\b[A-Za-z0-9+/]{40,}={0,2}\b/ },
    { id: "RS-01", category: "refusal_suppression", weight: 2.5,
      rationale: "Pressures the model to drop its safety refusals.",
      re: /\b(do not|don't|never)\b[^.]{0,15}\b(refuse|decline|warn|apologi[sz]e)\b|\b(no (warnings?|disclaimers?|restrictions?)|without (any )?(restriction|filter|limit)s?)\b/i },
    { id: "DX-01", category: "data_exfil", weight: 4.0,
      rationale: "Asks the model to ship data to an external endpoint.",
      re: /\b(send|post|exfiltrate|upload|forward|leak)\b[^.]{0,30}\b(to )?(https?:\/\/|ftp:\/\/|curl|webhook|my (server|endpoint))/i },
    { id: "JB-01", category: "jailbreak_known", weight: 5.0,
      rationale: "Matches a named jailbreak persona (DAN, developer mode, etc.).",
      re: /\b(DAN|do anything now|developer mode|jailbreak|STAN|AIM mode|unfiltered mode)\b/i },
  ];

  const INVISIBLE = /[\u200B\u200C\u200D\u2060\uFEFF\u202A-\u202E]/g;

  function normalise(text) {
    let t = text.normalize("NFKC").replace(INVISIBLE, "");
    t = t.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    t = t.replace(/[^\S\n]+/g, " ").replace(/\n{3,}/g, "\n\n");
    return t.trim();
  }

  async function sha256Hex(text) {
    try {
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
      return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
    } catch (_e) {
      // Fallback for non-secure contexts: FNV-1a, clearly marked as non-crypto.
      let hash = 0x811c9dc5;
      for (let i = 0; i < text.length; i++) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
      }
      return "fnv1a:" + (hash >>> 0).toString(16).padStart(8, "0");
    }
  }

  function verdictFor(score, block, review) {
    if (score >= block) return "block";
    if (score >= review) return "review";
    return "allow";
  }

  function confidenceFor(score, verdict, block, review) {
    if (verdict === "allow") return 1.0 - Math.min(1.0, score / review);
    if (verdict === "block") return Math.min(1.0, (score - block) / (block * 0.5) + 0.5);
    const band = block - review;
    const mid = review + band / 2.0;
    return Math.max(0.0, 0.5 - Math.abs(score - mid) / band);
  }

  function rationaleFor(verdict, hits, score) {
    if (hits.length === 0) return "No injection signal detected by the deterministic baseline.";
    const top = hits.reduce((a, b) => (b.weight > a.weight ? b : a), hits[0]);
    const named = [...new Set(hits.map((h) => h.rule_id))].sort().join(", ");
    const lead = { block: "Blocked", review: "Held for review", allow: "Allowed despite a weak signal" }[verdict];
    return `${lead} at score ${score.toFixed(1)}. Leading signal ${top.rule_id} (${top.category}): ${top.rationale} Rules fired: ${named}.`;
  }

  async function evaluate(prompt, opts) {
    const block = (opts && opts.block) || 7.0;
    const review = (opts && opts.review) || 3.0;
    const started = performance.now();
    const norm = normalise(prompt);
    const digest = await sha256Hex(prompt);

    const hits = [];
    let score = 0.0;
    for (const rule of RULES) {
      const m = rule.re.exec(norm);
      if (!m) continue;
      score += rule.weight;
      const snippet = m[0].length <= 48 ? m[0] : m[0].slice(0, 47) + "\u2026";
      hits.push({
        rule_id: rule.id, category: rule.category, weight: rule.weight,
        rationale: rule.rationale, snippet, span: [m.index, m.index + m[0].length],
      });
    }
    hits.sort((a, b) => b.weight - a.weight);
    const verdict = verdictFor(score, block, review);
    const categories = [...new Set(hits.map((h) => h.category))];

    return {
      verdict, score: Math.round(score * 1000) / 1000,
      confidence: Math.round(confidenceFor(score, verdict, block, review) * 1e4) / 1e4,
      prompt_sha256: digest, hits,
      rationale: rationaleFor(verdict, hits, score),
      latency_ms: Math.round((performance.now() - started) * 1000) / 1000,
      categories,
    };
  }

  window.ShomerGuardrail = { evaluate, sha256Hex, RULES, normalise };
})();
