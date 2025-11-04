
(async function main() {
  try {
    const { autoIndex, denylist } = await chrome.storage.sync.get(["autoIndex", "denylist"]);
    if (!autoIndex) return;

    const host = location.hostname;
    if (Array.isArray(denylist) && denylist.some(d => host.endsWith(d))) return;

    // Extract readable text (minimal). For better quality, plug Readability later.
    const text = document.body?.innerText || "";
    const title = document.title || location.href;
    if (!text || text.trim().length < 50) return;

    chrome.runtime.sendMessage({
      type: "INDEX_PAGE",
      url: location.href,
      title,
      text
    });
  } catch (e) {
    // fail silently
  }

  // Try pending highlight (background stored it just before opening this tab)
  try {
    const key = `highlight::${location.href}`;
    const data = await chrome.storage.session.get(key);
    const snippet = data[key];
    if (snippet) {
      highlightSnippet(snippet);
      await chrome.storage.session.remove(key);
    }
  } catch (e) {}
})();

chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "HIGHLIGHT") {
    highlightSnippet(msg.snippet);
  }
});

// --- naive highlighter with fuzzy fallback ---
function highlightSnippet(snippet) {
  if (!snippet || !snippet.trim()) return;
  // Try exact substring first
  if (document.body.innerText.includes(snippet)) {
    markText(snippet);
    return;
  }
  // Fuzzy: trim to first 100 chars and drop punctuation
  const f = normalize(snippet.slice(0, 100));
  const all = normalize(document.body.innerText);
  const idx = all.indexOf(f);
  if (idx !== -1) {
    // Recover approximate original segment by scanning DOM text nodes.
    markText(snippet.slice(0, 80));
  }
}

function normalize(s) {
  return (s || "").replace(/\s+/g, " ").replace(/[^\w\s]/g, "").toLowerCase();
}

// Wrap first occurrence with <mark>
function markText(target) {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  const needle = target;
  let node;
  while ((node = walker.nextNode())) {
    const i = node.nodeValue.indexOf(needle);
    if (i !== -1) {
      const range = document.createRange();
      range.setStart(node, i);
      range.setEnd(node, i + needle.length);
      const mark = document.createElement("mark");
      mark.className = "webmemory-hit";
      range.surroundContents(mark);
      mark.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
  }
}
