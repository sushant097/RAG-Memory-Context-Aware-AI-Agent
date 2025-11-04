const apiBaseEl = document.getElementById("apiBase");
const autoIndexEl = document.getElementById("autoIndex");
const denylistEl = document.getElementById("denylist");
const statusEl = document.getElementById("status");
const saveBtn = document.getElementById("save");

async function load() {
  const { apiBase, autoIndex, denylist } = await chrome.storage.sync.get(["apiBase","autoIndex","denylist"]);
  apiBaseEl.value = apiBase || "http://localhost:8000";
  autoIndexEl.checked = Boolean(autoIndex);
  denylistEl.value = (denylist || []).join("\n");
}
load();

saveBtn.addEventListener("click", async () => {
  const apiBase = apiBaseEl.value.trim();
  const autoIndex = autoIndexEl.checked;
  const denylist = denylistEl.value.split(/\n+/).map(s => s.trim()).filter(Boolean);
  await chrome.storage.sync.set({ apiBase, autoIndex, denylist });
  statusEl.textContent = "Saved!";
  setTimeout(() => statusEl.textContent = "", 1200);
});
