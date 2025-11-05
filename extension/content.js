(async function main() {
  const css = `
    mark.webmemory-hit {
      background: #fffb91;
      padding: 0 .15em;
      border-radius: 3px;
      box-shadow: 0 0 0 2px rgba(255,235,59,.35);
    }
  `;
  const style = document.createElement("style");
  style.textContent = css;
  document.documentElement.appendChild(style);

  // Always ping visit first
  try { chrome.runtime.sendMessage({ type: "VISIT", url: location.href }); } catch (e) {}

  // Try pending highlight from storage.session (older path still supported)
  try {
    const key = `highlight::${location.href}`;
    const data = await chrome.storage.session.get(key);
    const snippet = data[key];
    if (snippet) {
      highlight({ snippet, query: "" });
      await chrome.storage.session.remove(key);
    }
  } catch (e) {}

  // Auto-index (unchanged safety; VISIT was already sent above)
  try {
    const { autoIndex, denylist } = await chrome.storage.sync.get(["autoIndex", "denylist"]);
    const host = location.hostname;
    if (!autoIndex) return;
    if (Array.isArray(denylist) && denylist.some(d => host.endsWith(d))) return;

    const text = document.body?.innerText || "";
    const title = document.title || location.href;
    if (text && text.trim().length >= 50) {
      chrome.runtime.sendMessage({ type: "INDEX_PAGE", url: location.href, title, text });
    }
  } catch (e) {}
})();

// Listen for background-triggered highlight after the tab loads
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "HIGHLIGHT") highlight({ snippet: msg.snippet, query: msg.query });
});

// ---- Highlight helpers ----
function highlight({ snippet, query }) {
  // 1) Try exact snippet first
  if (snippet && snippet.trim()) {
    const ok = markFirst(snippet.trim());
    if (ok) return;
  }
  // 2) Fallback: highlight query terms (>=3 chars)
  const terms = (query || "").split(/\s+/).map(t => t.trim()).filter(t => t.length >= 3);
  if (terms.length) markTerms(terms);
}

function markFirst(target) {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  let node, found = false;
  while ((node = walker.nextNode())) {
    const i = node.nodeValue.toLowerCase().indexOf(target.toLowerCase());
    if (i !== -1) {
      const range = document.createRange();
      range.setStart(node, i);
      range.setEnd(node, i + target.length);
      wrapRange(range);
      found = true;
      break;
    }
  }
  return found;
}

function markTerms(terms) {
  // Build a case-insensitive regex for all terms
  const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!escaped.length) return;
  const re = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  const ranges = [];
  let node;
  while ((node = walker.nextNode())) {
    let m;
    while ((m = re.exec(node.nodeValue)) !== null) {
      const range = document.createRange();
      range.setStart(node, m.index);
      range.setEnd(node, m.index + m[0].length);
      ranges.push(range);
      // Avoid infinite loops on 0-length matches
      if (re.lastIndex === m.index) re.lastIndex++;
    }
  }
  // Apply marks (limit to avoid over-highlighting)
  ranges.slice(0, 200).forEach(wrapRange);
  // Scroll to the first hit
  const first = document.querySelector("mark.webmemory-hit");
  if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
}

function wrapRange(range) {
  const mark = document.createElement("mark");
  mark.className = "webmemory-hit";
  try { range.surroundContents(mark); }
  catch {
    // If the range crosses nodes, fallback: wrap a cloned span
    const span = document.createElement("mark");
    span.className = "webmemory-hit";
    span.textContent = range.toString();
    range.deleteContents();
    range.insertNode(span);
  }
}
