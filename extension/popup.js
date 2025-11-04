const q = document.getElementById("q");
const go = document.getElementById("go");
const resultsEl = document.getElementById("results");

// settings button is optional; guard it
const openBtn = document.getElementById("openOptions");
if (openBtn && chrome?.runtime?.openOptionsPage) {
  openBtn.addEventListener("click", () => chrome.runtime.openOptionsPage());
}

go.addEventListener("click", doSearch);
q.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

function renderResult(r) {
  const el = document.createElement("div");
  el.className = "result";
  el.innerHTML = `
    <div class="title">${escapeHtml(r.title || r.url)}</div>
    <div class="snippet">${escapeHtml(r.snippet)}</div>
  `;
  el.addEventListener("click", async () => {
    try {
      const query = q.value.trim();
      chrome.runtime.sendMessage({
        type: "OPEN_AND_HIGHLIGHT",
        url: r.url,
        snippet: r.snippet,
        query
      });
      window.close();
    } catch (e) {
      console.error("OPEN_AND_HIGHLIGHT failed:", e);
    }
  });
  resultsEl.appendChild(el);
}

async function doSearch() {
  resultsEl.textContent = "Searching…";
  const query = (q.value || "").trim();
  if (!query) { resultsEl.textContent = ""; return; }

  try {
    const resp = await chrome.runtime.sendMessage({ type: "SEARCH", query, topK: 5 });
    if (!resp?.ok) {
      resultsEl.textContent = "Search failed.";
      return;
    }
    const results = Array.isArray(resp.results) ? resp.results : [];
    if (results.length === 0) {
      resultsEl.textContent = "No results.";
      return;
    }
    resultsEl.innerHTML = "";
    results.forEach(renderResult);
  } catch (e) {
    console.error("SEARCH failed:", e);
    resultsEl.textContent = "Search failed.";
  }
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
