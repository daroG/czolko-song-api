const tbody = document.querySelector("#songs tbody");
const statusEl = document.querySelector("#status");

function setStatus(msg) { statusEl.textContent = msg; }

async function api(method, url, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${method} ${url} -> ${res.status}`);
  return res.status === 204 ? null : res.json();
}

function escapeAttr(s) { return String(s).replace(/"/g, "&quot;"); }

function row(song) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input value="${escapeAttr(song.author)}" data-field="author" /></td>
    <td><input value="${escapeAttr(song.title)}" data-field="title" /></td>
    <td><button data-save>Zapisz</button> <button data-del>Usuń</button></td>`;
  const get = (f) => tr.querySelector(`[data-field="${f}"]`).value;
  tr.querySelector("[data-save]").onclick = async () => {
    try { await api("PUT", `/api/songs/${song.id}`, { author: get("author"), title: get("title") });
      setStatus("Zapisano."); } catch (e) { setStatus(e.message); }
  };
  tr.querySelector("[data-del]").onclick = async () => {
    try { await api("DELETE", `/api/songs/${song.id}`); tr.remove(); setStatus("Usunięto."); }
    catch (e) { setStatus(e.message); }
  };
  return tr;
}

async function load() {
  tbody.replaceChildren();
  const songs = await api("GET", "/api/songs");
  for (const s of songs) tbody.appendChild(row(s));
  setStatus(`${songs.length} piosenek.`);
}

document.querySelector("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api("POST", "/api/songs", { author: f.author.value, title: f.title.value });
    f.reset(); await load();
  } catch (err) { setStatus(err.message); }
});

load().catch((e) => setStatus(e.message));
