
// Defaults on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({
    apiBase: "http://localhost:8000",
    autoIndex: true,
    denylist: [
      "mail.google.com",
      "web.whatsapp.com",
      "teams.microsoft.com",
      "slack.com",
      "accounts.google.com",
      "localhost"
    ]
  });
});

// Helper: POST JSON
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"content-type":"application/json"},
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// Listen for messages from content/popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    const { apiBase } = await chrome.storage.sync.get(["apiBase"]);

    if (msg?.type === "INDEX_PAGE") {
      try {
        const res = await postJSON(`${apiBase}/index_page`, {
          url: msg.url,
          title: msg.title,
          text: msg.text
        });
        sendResponse({ ok: true, result: res });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
      return; // keep channel open
    }

    if (msg?.type === "SEARCH") {
      try {
        const u = new URL(`${apiBase}/search`);
        u.searchParams.set("q", msg.query);
        u.searchParams.set("top_k", String(msg.topK ?? 5));
        const r = await fetch(u.toString());
        const results = await r.json();
        sendResponse({ ok: true, results });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
      return;
    }

    if (msg?.type === "OPEN_AND_HIGHLIGHT") {
      const { url, snippet, query } = msg;

      // Build a text fragment from snippet or query (trim & shorten to stay safe)
      const fragSource = (snippet && snippet.trim().length > 0 ? snippet : query) || "";
      const frag = encodeURIComponent(fragSource.slice(0, 150)).replace(/%20/g, " ");
      const urlWithFrag = fragSource ? `${url}#:~:text=${frag}` : url;

      // Open the tab
      const tab = await chrome.tabs.create({ url: urlWithFrag });

      // When the tab finishes loading, ask content.js to highlight again (fallback)
      const listener = async (tabId, changeInfo, updatedTab) => {
        if (tabId === tab.id && changeInfo.status === "complete") {
          chrome.tabs.sendMessage(tab.id, { type: "HIGHLIGHT", snippet, query });
          chrome.tabs.onUpdated.removeListener(listener);
        }
      };
      chrome.tabs.onUpdated.addListener(listener);

      sendResponse({ ok: true, tabId: tab.id });
      return;
    }

    if (msg?.type === "VISIT") {
      try {
        const { apiBase } = await chrome.storage.sync.get(["apiBase"]);
        const r = await fetch(`${apiBase}/visit`, {
          method: "POST",
          headers: {"content-type":"application/json"},
          body: JSON.stringify({ url: msg.url })
        });
        const json = await r.json();
        sendResponse({ ok: true, result: json });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
      return; // async
    }

  })();
  // Indicate async response
  return true;
});
