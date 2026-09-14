#!/usr/bin/env python3
"""Compose the copy-editor artifact from pages.json."""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path("/home/user/marci-rmt-website")
pages = json.loads((HERE / "pages.json").read_text())

total_blocks = sum(p["srcdoc"].count('data-copy-id="') for p in pages)
payload = json.dumps(pages, ensure_ascii=False).replace("<", "\\u003c")

HTML = r"""<title>Marci.RMT Copy Editor</title>
<style>
:root {
  --bar:#161a20; --panel:#212731; --panel-2:#2b323e; --line:#39414f;
  --fg:#e7eaee; --fg-dim:#8d96a5; --fg-mute:#646d7b;
  --amber:#d98324; --teal:#3a7d6c; --teal-lift:#4d9683;
  --ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --bar-h: 52px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bar);color:var(--fg);font-family:var(--ui);font-size:13px}

/* ---------- top bar ---------- */
.bar{
  position:fixed;inset:0 0 auto 0;height:var(--bar-h);z-index:50;
  display:flex;align-items:center;gap:14px;padding:0 14px;
  background:var(--bar);border-bottom:1px solid var(--line);
}
.mark{font-weight:600;letter-spacing:-.01em;white-space:nowrap}
.mark span{color:var(--teal-lift)}
.sep{width:1px;height:22px;background:var(--line);flex:none}

select.pick{
  appearance:none;background:var(--panel);color:var(--fg);border:1px solid var(--line);
  border-radius:6px;padding:7px 30px 7px 11px;font:inherit;font-weight:500;cursor:pointer;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M1 1l4 4 4-4' fill='none' stroke='%238d96a5' stroke-width='1.5'/></svg>");
  background-repeat:no-repeat;background-position:right 10px center;
  max-width:230px;text-overflow:ellipsis;
}
select.pick:focus-visible,button:focus-visible{outline:2px solid var(--amber);outline-offset:2px}

.nav-btn{
  background:var(--panel);color:var(--fg-dim);border:1px solid var(--line);border-radius:6px;
  width:30px;height:30px;font-size:14px;cursor:pointer;flex:none;line-height:1;
}
.nav-btn:hover:not(:disabled){background:var(--panel-2);color:var(--fg)}
.nav-btn:disabled{opacity:.35;cursor:default}

.status{display:flex;align-items:center;gap:7px;color:var(--fg-dim);white-space:nowrap}
.dot{width:7px;height:7px;border-radius:50%;background:var(--fg-mute);flex:none}
.status[data-s="dirty"] .dot{background:var(--amber)}
.status[data-s="saving"] .dot{background:var(--amber);animation:pulse 1s ease-in-out infinite}
.status[data-s="saved"] .dot{background:var(--teal-lift)}
.status[data-s="off"] .dot{background:#c0554a}
@keyframes pulse{50%{opacity:.3}}
@media(prefers-reduced-motion:reduce){.status .dot{animation:none}}

.pagecount{color:var(--teal-lift);white-space:nowrap;font-variant-numeric:tabular-nums}
.pagecount:empty{display:none}
.count{margin-left:auto;display:flex;align-items:center;gap:10px;color:var(--fg-dim);white-space:nowrap}
.count b{color:var(--fg);font-variant-numeric:tabular-nums;font-weight:600}

.ghost{
  background:transparent;color:var(--fg-dim);border:1px solid var(--line);border-radius:6px;
  padding:7px 11px;font:inherit;cursor:pointer;white-space:nowrap;
}
.ghost:hover{background:var(--panel);color:var(--fg)}
.ghost[aria-pressed="true"]{background:var(--panel-2);color:var(--fg);border-color:var(--fg-mute)}

/* ---------- drawers ---------- */
.drawer{
  position:fixed;left:0;right:0;top:var(--bar-h);z-index:40;
  max-height:calc(100vh - var(--bar-h) - 40px);overflow-y:auto;
  background:var(--panel);border-bottom:1px solid var(--line);
  padding:18px 20px 20px;
}
.drawer[hidden]{display:none}
.drawer h2{margin:0 0 10px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--fg-mute);font-weight:600}
.help-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px 26px;max-width:1100px}
.help-grid p{margin:0;color:var(--fg-dim);line-height:1.55}
.help-grid p b{color:var(--fg);font-weight:600}
kbd{
  font-family:var(--mono);font-size:11px;background:var(--panel-2);color:var(--fg);
  border:1px solid var(--line);border-bottom-width:2px;border-radius:4px;padding:1px 5px;
}
.chip{display:inline-block;background:var(--amber);color:#fff;font-family:var(--mono);
  font-size:9px;letter-spacing:.08em;padding:1px 4px;border-radius:2px;vertical-align:1px}

.meta-field{display:block;margin-bottom:14px;max-width:820px}
.meta-field span{display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--fg-mute);margin-bottom:6px;font-weight:600}
.meta-field input,.meta-field textarea{
  width:100%;background:var(--bar);color:var(--fg);border:1px solid var(--line);
  border-radius:6px;padding:9px 11px;font:inherit;line-height:1.5;resize:vertical;
}
.meta-field input:focus,.meta-field textarea:focus{outline:2px solid var(--amber);outline-offset:-1px;border-color:transparent}
.meta-note{color:var(--fg-mute);margin:-6px 0 16px;max-width:820px;line-height:1.5}

/* ---------- stage ---------- */
.stage{position:fixed;inset:var(--bar-h) 0 0 0;background:#f4f1ea}
.stage.pushed{top:calc(var(--bar-h) + var(--drawer-h,0px))}
iframe{width:100%;height:100%;border:0;display:block;background:#f4f1ea}

.toast{
  position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:60;
  background:var(--panel-2);color:var(--fg);border:1px solid var(--line);
  border-radius:7px;padding:9px 15px;box-shadow:0 8px 28px rgba(0,0,0,.45);
  opacity:0;pointer-events:none;transition:opacity .16s, transform .16s;
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(-3px)}
.toast b{color:var(--amber)}

.banner{
  position:fixed;left:0;right:0;top:var(--bar-h);z-index:45;
  background:#3a2420;color:#f0d9d4;border-bottom:1px solid #5c3a33;
  padding:9px 16px;font-size:12.5px;line-height:1.5;
}
.banner[hidden]{display:none}

@media (max-width:760px){
  .mark,.count span.lbl{display:none}
  select.pick{max-width:150px}
}
</style>

<div class="bar">
  <div class="mark">Marci<span>.</span>RMT <span style="color:var(--fg-mute);font-weight:400">copy</span></div>
  <div class="sep"></div>
  <button class="nav-btn" id="prev" title="Previous page" aria-label="Previous page">‹</button>
  <select class="pick" id="pick" aria-label="Choose a page to edit"></select>
  <button class="nav-btn" id="next" title="Next page" aria-label="Next page">›</button>
  <div class="status" id="status" data-s="idle"><span class="dot"></span><span id="statusText">Ready</span></div>
  <span id="pageEdits" class="pagecount"></span>
  <div class="count">
    <span class="lbl" style="color:var(--fg-mute)">Edited</span>
    <span><b id="nEdited">0</b> <span style="color:var(--fg-mute)">/ __TOTAL__</span></span>
    <button class="ghost" id="metaBtn" aria-pressed="false">Page title</button>
    <button class="ghost" id="helpBtn" aria-pressed="false">How this works</button>
  </div>
</div>

<div class="drawer" id="help" hidden>
  <h2>How this works</h2>
  <div class="help-grid">
    <p><b>Click any text and type.</b> Everything on the page that is copy can be edited straight in place. Hovering shows you what's editable.</p>
    <p><b>Your edits save on their own</b>, a moment after you stop typing. The dot next to the page name turns green when a change is stored.</p>
    <p><b>Changed text gets a green bar</b> down its left side, so you can see at a glance what you've touched on a page.</p>
    <p><b>Press <kbd>Esc</kbd> to undo a block</b> back to its original wording while your cursor is still in it.</p>
    <p><b>An orange <span class="chip">T1</span> tag</b> marks copy I flagged as reading AI-generated. Hover it to read why. Editing the block clears the flag.</p>
    <p><b>Click the site's own menu to move around</b> — Services, About, Areas Served and the rest all work, as do links in the footer and body. A green outline means a link will take you there.</p>
    <p><b>Or use the page menu above</b>, which lists all 21 pages and shows a ✓ count next to any page you've already edited. <kbd>Alt</kbd>+<kbd>←</kbd> / <kbd>→</kbd> pages through them.</p>
    <p><b>Nothing here touches the live site.</b> When you're done, tell me and I'll merge your wording into the real pages.</p>
    <p><b>Button labels are copy too</b> — clicking one like "Read the full story" puts your cursor in it rather than navigating. Use the top menu to get to that page.</p>
    <p><b>Images, prices and layout</b> aren't editable in this view. Tell me about those in chat and I'll change them directly.</p>
  </div>
</div>

<div class="drawer" id="meta" hidden>
  <h2>Browser tab &amp; Google search result</h2>
  <p class="meta-note">This text never appears on the page itself. The title shows in the browser tab and as the blue headline in Google; the description is the grey summary underneath it.</p>
  <label class="meta-field"><span>Page title</span><input type="text" id="metaTitle" /></label>
  <label class="meta-field"><span>Search description</span><textarea id="metaDesc" rows="2"></textarea></label>
</div>

<div class="banner" id="offline" hidden>
  <b>Heads up:</b> this view can't save. You can still type to try wording out, but nothing will be kept when you close the tab — tell me and I'll look into it.
</div>

<div class="stage" id="stage"><iframe id="frame" title="Page preview"></iframe></div>
<div class="toast" id="toast"></div>

<script>
const PAGES = __PAYLOAD__;
const TOTAL = __TOTAL__;

const $ = id => document.getElementById(id);
const frame = $("frame"), pick = $("pick"), stage = $("stage");
let db = null, edits = {}, cur = 0, saveTimer = null, pendingPages = new Set();

/* ---------- page menu ---------- */
(function buildMenu(){
  let group = null;
  PAGES.forEach((p,i)=>{
    if(p.group !== group){ group = p.group;
      const og = document.createElement("optgroup"); og.label = group; og.dataset.g = group; pick.appendChild(og); }
    const o = document.createElement("option");
    o.value = i; o.textContent = p.label;
    pick.lastElementChild.appendChild(o);
  });
})();

function setStatus(s, text){ $("status").dataset.s = s; $("statusText").textContent = text; }

function countEdited(){
  let n = 0;
  for(const k in edits) n += Object.keys(edits[k]||{}).length;
  $("nEdited").textContent = n;
  const here = Object.keys(edits[PAGES[cur].key] || {}).length;
  $("pageEdits").textContent = here ? `${here} edited here` : "";
  // mark pages that have edits, so the menu shows where you've been
  [...pick.options].forEach(o=>{
    const k = PAGES[+o.value].key, c = Object.keys(edits[k]||{}).length;
    o.textContent = PAGES[+o.value].label + (c ? `  ✓ ${c}` : "");
  });
}

function toast(msg){
  const t = $("toast"); t.innerHTML = msg; t.classList.add("show");
  clearTimeout(t._t); t._t = setTimeout(()=>t.classList.remove("show"), 2200);
}

/* ---------- persistence ---------- */
async function connect(){
  try { db = await claude.use("db"); } catch(e){ db = null; }
  if(!db){ $("offline").hidden = false; setStatus("off","Not saving"); layout(); return; }
  try{
    const snap = await db.collection("edits").get();
    snap.docs.forEach(d => { const v = d.data(); if(v && v.blocks) edits[d.id] = {...v.blocks}; });
    countEdited(); applyEdits();
    setStatus(Object.keys(edits).length ? "saved" : "idle",
              Object.keys(edits).length ? "Edits loaded" : "Ready");
  }catch(e){ setStatus("off","Couldn't load"); }
}

function queueSave(pageKey){
  pendingPages.add(pageKey);
  setStatus("dirty","Unsaved");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flush, 700);
}

async function flush(){
  if(!db || !pendingPages.size) return;
  const keys = [...pendingPages]; pendingPages.clear();
  setStatus("saving","Saving…");
  try{
    await Promise.all(keys.map(k =>
      db.doc("edits/"+k).set({ blocks: edits[k] || {}, updatedAt: new Date().toISOString() })));
    setStatus("saved","Saved");
  }catch(err){
    keys.forEach(k => pendingPages.add(k));
    setStatus("off", err && err.code === "revoked" ? "Not saving" : "Save failed");
  }
}
window.addEventListener("beforeunload", flush);

/* ---------- the editable surface ---------- */
function applyEdits(){
  const doc = frame.contentDocument; if(!doc) return;
  const key = PAGES[cur].key, stored = edits[key] || {};
  doc.querySelectorAll("[data-copy-id]").forEach(el=>{
    const id = el.dataset.copyId;
    if(Object.prototype.hasOwnProperty.call(stored, id)) el.textContent = stored[id];
    mark(el);
  });
}

function mark(el){
  const id = el.dataset.copyId, key = PAGES[cur].key;
  const changed = (edits[key]||{})[id] !== undefined
    && norm(el.textContent) !== norm(el.dataset.copyOrig);
  el.classList.toggle("is-changed", changed);
  if(changed) el.removeAttribute("data-copy-flag");
  else if(el.dataset.copyNote) el.setAttribute("data-copy-flag", flagOf(el.dataset.copyNote));
}

const norm = s => (s||"").replace(/\s+/g," ").trim();
const flagOf = note => (note.match(/\bT(\d)\b/) || [,"?"])[1] === "?" ? "note" : "T"+note.match(/\bT(\d)\b/)[1];

function wire(){
  const doc = frame.contentDocument; if(!doc) return;
  const key = PAGES[cur].key;

  doc.querySelectorAll("[data-copy-id]").forEach(el=>{
    el.setAttribute("contenteditable", "plaintext-only");
    if(el.contentEditable !== "plaintext-only") el.setAttribute("contenteditable","true");
    el.setAttribute("spellcheck","true");
    if(el.dataset.copyNote) el.title = el.dataset.copyNote;
  });

  doc.addEventListener("input", e=>{
    const el = e.target.closest?.("[data-copy-id]"); if(!el) return;
    const id = el.dataset.copyId;
    edits[key] = edits[key] || {};
    if(norm(el.textContent) === norm(el.dataset.copyOrig)) delete edits[key][id];
    else edits[key][id] = norm(el.textContent);
    mark(el); countEdited(); queueSave(key);
  });

  doc.addEventListener("blur", e=>{
    if(e.target.closest?.("[data-copy-id]")) flush();
  }, true);

  doc.addEventListener("keydown", e=>{
    const el = e.target.closest?.("[data-copy-id]"); if(!el) return;
    if(e.key === "Escape"){
      e.preventDefault();
      el.textContent = el.dataset.copyOrig;
      delete (edits[key]||{})[el.dataset.copyId];
      mark(el); countEdited(); queueSave(key);
      toast("Reverted to the original wording");
      el.blur();
    }
    if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); el.blur(); }
  });

  // paste as plain text, so nothing carries formatting in from elsewhere
  doc.addEventListener("paste", e=>{
    const el = e.target.closest?.("[data-copy-id]"); if(!el) return;
    e.preventDefault();
    const txt = (e.clipboardData || frame.contentWindow.clipboardData).getData("text");
    frame.contentDocument.execCommand("insertText", false, norm(txt));
  });

  // the site's own links drive the editor
  doc.addEventListener("click", e=>{
    const a = e.target.closest("a"); if(!a) return;
    e.preventDefault();
    if(a.hasAttribute("data-copy-id")) return;   // it's copy — let the cursor land
    const to = a.getAttribute("data-goto");
    if(to){
      const i = PAGES.findIndex(p => p.key === to);
      if(i >= 0){ show(i, a.getAttribute("data-goto-hash") || ""); return; }
    }
    const ext = a.getAttribute("data-external");
    if(ext) toast(ext.startsWith("mailto:") || ext.startsWith("tel:")
      ? "That's your contact link — it works on the live site."
      : "That link opens <b>" + ext.replace(/^https?:\/\//,"").split("/")[0] + "</b> on the live site.");
  });
}

/* ---------- navigation ---------- */
let pendingHash = "";
function show(i, hash){
  flush();
  pendingHash = hash || "";
  cur = Math.max(0, Math.min(PAGES.length-1, i));
  pick.value = cur;
  $("prev").disabled = cur === 0;
  $("next").disabled = cur === PAGES.length-1;
  const p = PAGES[cur];
  $("metaTitle").value = p.meta.title || "";
  $("metaDesc").value  = p.meta.description || "";
  frame.srcdoc = p.srcdoc;
  countEdited();
}

frame.addEventListener("load", ()=>{
  wire(); applyEdits();
  if(pendingHash){
    const t = frame.contentDocument.getElementById(pendingHash);
    if(t) t.scrollIntoView({block:"start"});
    pendingHash = "";
  }
});
pick.addEventListener("change", ()=> show(+pick.value));
document.addEventListener("keydown", e=>{
  if(e.target.closest("input,textarea,select")) return;
  if(e.altKey && e.key === "ArrowLeft"){ e.preventDefault(); show(cur-1); }
  if(e.altKey && e.key === "ArrowRight"){ e.preventDefault(); show(cur+1); }
});
$("prev").addEventListener("click", ()=> show(cur-1));
$("next").addEventListener("click", ()=> show(cur+1));

/* ---------- meta fields ---------- */
function metaSave(){
  const key = PAGES[cur].key;
  edits[key] = edits[key] || {};
  const t = $("metaTitle").value.trim(), d = $("metaDesc").value.trim();
  if(t && t !== PAGES[cur].meta.title) edits[key]["__title"] = t; else delete edits[key]["__title"];
  if(d && d !== PAGES[cur].meta.description) edits[key]["__description"] = d; else delete edits[key]["__description"];
  countEdited(); queueSave(key);
}
$("metaTitle").addEventListener("input", metaSave);
$("metaDesc").addEventListener("input", metaSave);

/* ---------- drawers ---------- */
function drawer(btnId, panelId, other){
  const btn = $(btnId), panel = $(panelId);
  btn.addEventListener("click", ()=>{
    const open = panel.hidden;
    if(open && other){ $(other).hidden = true; }
    panel.hidden = !open;
    btn.setAttribute("aria-pressed", String(open));
    document.querySelectorAll(".ghost").forEach(b=>{
      if(b !== btn) b.setAttribute("aria-pressed", String(!$(b.id === "helpBtn" ? "help" : "meta").hidden));
    });
    layout();
  });
}
drawer("helpBtn","help","meta");
drawer("metaBtn","meta","help");

function layout(){
  const bannerH = $("offline").hidden ? 0 : $("offline").offsetHeight;
  document.querySelectorAll(".drawer").forEach(d=>{
    d.style.top = `calc(var(--bar-h) + ${bannerH}px)`;
  });
  const open = [...document.querySelectorAll(".drawer")].find(d=>!d.hidden);
  stage.style.top = `calc(var(--bar-h) + ${bannerH + (open ? open.offsetHeight : 0)}px)`;
}
window.addEventListener("resize", layout);

/* ---------- go ---------- */
show(0);
connect();
</script>
"""

out = (HTML
       .replace("__PAYLOAD__", payload)
       .replace("__TOTAL__", str(total_blocks)))
(ROOT / "copy-editor.html").write_text(out, encoding="utf-8")
print(f"wrote copy-editor.html  ({len(out)//1024} KB, {total_blocks} editable blocks)")
