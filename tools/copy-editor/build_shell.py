#!/usr/bin/env python3
"""Compose the copy-editor artifact from pages.json."""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[1]
pages = json.loads((HERE / "pages.json").read_text())

total_blocks = sum(p["srcdoc"].count('data-copy-id="') for p in pages)
payload = json.dumps(pages, ensure_ascii=False).replace("<", "\\u003c")

HTML = r"""<title>Marci.RMT Rewrite</title>
<style>
/* A dark editing chrome around the real (light) site pages. Single theme on purpose. */
:root {
  color-scheme: dark;
  --bar:#161a20; --panel:#212731; --panel-2:#2b323e; --line:#39414f;
  --fg:#e7eaee; --fg-dim:#8d96a5; --fg-mute:#646d7b;
  --amber:#d98324; --teal:#3a7d6c; --teal-lift:#4d9683;
  --ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --bar-h: 52px;
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bar);color:var(--fg);font-family:var(--ui);font-size:13px}

/* ---------- top bar ---------- */
.bar{
  position:fixed;inset:0 0 auto 0;height:calc(var(--bar-h) + var(--safe-top));z-index:50;
  display:flex;align-items:center;gap:14px;padding:var(--safe-top) 14px 0;
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
  position:fixed;left:0;right:0;top:calc(var(--bar-h) + var(--safe-top));z-index:40;
  max-height:calc(100vh - var(--bar-h) - var(--safe-top) - 40px);overflow-y:auto;
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
.stage{position:fixed;inset:calc(var(--bar-h) + var(--safe-top)) 0 var(--safe-bottom) 0;background:#f4f1ea}
iframe{width:100%;height:100%;border:0;display:block;background:#f4f1ea}

.toast{
  position:fixed;left:50%;bottom:calc(22px + var(--safe-bottom));transform:translateX(-50%);z-index:60;
  max-width:calc(100vw - 32px);
  background:var(--panel-2);color:var(--fg);border:1px solid var(--line);
  border-radius:7px;padding:9px 15px;box-shadow:0 8px 28px rgba(0,0,0,.45);
  opacity:0;pointer-events:none;transition:opacity .16s, transform .16s;
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(-3px)}
.toast b{color:var(--amber)}

.banner{
  position:fixed;left:0;right:0;top:calc(var(--bar-h) + var(--safe-top));z-index:45;
  background:#3a2420;color:#f0d9d4;border-bottom:1px solid #5c3a33;
  padding:9px 16px;font-size:12.5px;line-height:1.5;
}
.banner[hidden]{display:none}

.ghost .short{display:none}

/* Phones: keep the page menu, the save dot, the count and both buttons on one
   row. The arrows, labels and per-page count are extras the menu covers. */
@media (max-width:760px){
  .bar{gap:8px}
  .mark,.sep,#prev,#next,#pageEdits,#statusText,.count span.lbl{display:none}
  .count{gap:8px}
  select.pick{max-width:130px}
  .ghost{padding:7px 9px}
  .ghost .long{display:none}
  .ghost .short{display:inline}
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
    <span class="lbl" style="color:var(--fg-mute)">In your words</span>
    <span><b id="nEdited">0</b> <span style="color:var(--fg-mute)">/ __TOTAL__</span></span>
    <button class="ghost" id="metaBtn" aria-pressed="false"><span class="long">Page title</span><span class="short">Title</span></button>
    <button class="ghost" id="helpBtn" aria-pressed="false"><span class="long">How this works</span><span class="short">Help</span></button>
  </div>
</div>

<div class="drawer" id="help" hidden>
  <h2>How this works</h2>
  <div class="help-grid">
    <p><b>Click any text and type.</b> Everything on the page that is copy can be edited straight in place. Hovering shows you what's editable.</p>
    <p><b>Your edits save on their own</b>, a moment after you stop typing. The dot next to the page name turns green when a change is stored.</p>
    <p><b>A green bar means it's in your words.</b> That covers anything you change here, plus text you'd already rewritten before, which is carried over. The count at the top right tracks how much of the site is yours.</p>
    <p><b>Press <kbd>Esc</kbd> to undo a block</b> back to its starting wording while your cursor is still in it.</p>
    <p><b>An orange <span class="chip">T1</span> tag</b> marks copy I flagged as reading AI-generated; a <span class="chip">note</span> tag is a heads-up about something I changed. Hover either to read it. Editing the block clears the tag.</p>
    <p><b>Want something gone?</b> Clear all its text. It stays on screen as "Removed" so you can bring it back with <kbd>Esc</kbd>, and I'll take it out of the page when I merge.</p>
    <p><b>Click the site's own menu to move around.</b> Services, Events, About, FAQ and Contact all work, as do links in the footer and body. A green outline means a link will take you there.</p>
    <p><b>Or use the page menu above</b>, which shows how many blocks on each page are in your words. <kbd>Alt</kbd>+<kbd>←</kbd> / <kbd>→</kbd> pages through them.</p>
    <p><b>Button labels are copy too.</b> Clicking one like "Read the full story" puts your cursor in it rather than navigating.</p>
    <p><b>The footer is shared by every page.</b> Edit it on Home and the change applies everywhere.</p>
    <p><b>Nothing here touches the live site.</b> When you're done, tell me and I'll merge your wording into the real pages.</p>
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

// Blocks on a page that are in Marci's words: already-yours text carried in
// from the deck, plus anything edited here. Only blocks still on the page
// count, so a saved edit for a block that has since been removed doesn't;
// title/description edits live in the chrome and aren't page blocks.
function yoursOn(p){
  const known = new Set(p.ids || []), ids = new Set(p.mine || []);
  Object.keys(edits[p.key] || {}).forEach(id => { if(known.has(id)) ids.add(id); });
  return ids.size;
}

function countEdited(){
  $("nEdited").textContent = PAGES.reduce((n, p) => n + yoursOn(p), 0);
  const p = PAGES[cur], here = yoursOn(p);
  $("pageEdits").textContent = here ? `${here} of ${p.blocks} yours here` : "";
  // the menu shows how far along each page is
  [...pick.options].forEach(o=>{
    const q = PAGES[+o.value], c = yoursOn(q);
    o.textContent = q.label + (c ? `  ✓ ${c}/${q.blocks}` : "");
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

// One write at a time per page document: a second save queues behind the
// first and sends whatever the page's edits are when its turn comes, so an
// older save can never land after a newer one.
const inflight = {};
function writePage(k){
  const run = (inflight[k] || Promise.resolve()).catch(()=>{}).then(() =>
    db.doc("edits/"+k).set({ blocks: {...(edits[k] || {})}, updatedAt: new Date().toISOString() }));
  inflight[k] = run;
  return run;
}

async function flush(){
  if(!db || !pendingPages.size) return;
  const keys = [...pendingPages]; pendingPages.clear();
  setStatus("saving","Saving…");
  try{
    await Promise.all(keys.map(writePage));
    if(!pendingPages.size) setStatus("saved","Saved");
  }catch(err){
    keys.forEach(k => pendingPages.add(k));
    setStatus("off", err && (err.code === "revoked" || err.code === "invalid_argument")
      ? "Not saving" : "Save failed");
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
  el.classList.toggle("is-changed", changed || el.hasAttribute("data-copy-mine"));
  el.classList.toggle("is-empty", !norm(el.textContent));
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
    // A button label is usually a <span> inside the link, so check the click
    // target, not just the <a>: if it lands on copy, let the cursor land.
    if(e.target.closest("[data-copy-id]")) return;
    const to = a.getAttribute("data-goto");
    if(to){
      const i = PAGES.findIndex(p => p.key === to);
      if(i >= 0){ show(i, a.getAttribute("data-goto-hash") || ""); return; }
    }
    const ext = a.getAttribute("data-external");
    if(ext) toast(ext.startsWith("mailto:") || ext.startsWith("tel:")
      ? "That's your email link. It works on the live site."
      : "That link opens <b>" + ext.replace(/^https?:\/\//,"").split("/")[0] + "</b> on the live site.");
  });
}

/* ---------- navigation ---------- */
// Wire a page as soon as its text is parsed. The iframe's load event waits
// for every font and image, so a slow font host would leave the page on
// screen but not yet editable. `nav` makes sure that if pages are flipped
// quickly, only the last one shown gets wired.
let nav = 0;
function whenParsed(gen, before, cb){
  const d = frame.contentDocument;
  if(gen !== nav) return;
  if(d && d !== before && d.readyState !== "loading") return cb();
  setTimeout(()=> whenParsed(gen, before, cb), 25);
}

function show(i, hash){
  flush();
  cur = Math.max(0, Math.min(PAGES.length-1, i));
  pick.value = cur;
  $("prev").disabled = cur === 0;
  $("next").disabled = cur === PAGES.length-1;
  const p = PAGES[cur];
  $("metaTitle").value = p.meta.title || "";
  $("metaDesc").value  = p.meta.description || "";
  const gen = ++nav, before = frame.contentDocument;
  frame.srcdoc = p.srcdoc;
  whenParsed(gen, before, ()=>{
    wire(); applyEdits();
    const t = hash && frame.contentDocument.getElementById(hash);
    if(t) t.scrollIntoView({block:"start"});
  });
  countEdited();
}
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
    d.style.top = `calc(var(--bar-h) + var(--safe-top) + ${bannerH}px)`;
  });
  const open = [...document.querySelectorAll(".drawer")].find(d=>!d.hidden);
  stage.style.top = `calc(var(--bar-h) + var(--safe-top) + ${bannerH + (open ? open.offsetHeight : 0)}px)`;
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
