
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
      // Save the snippet in session storage under its URL, then open the tab.
      const { url, snippet } = msg;
      const key = `highlight::${url}`;
      await chrome.storage.session.set({ [key]: snippet });

      const tab = await chrome.tabs.create({ url });
      // Content will read storage.session on load and highlight.
      sendResponse({ ok: true, tabId: tab.id });
      return;
    }
  })();
  // Indicate async response
  return true;
});
