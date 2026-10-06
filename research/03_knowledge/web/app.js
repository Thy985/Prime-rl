/* ===== app.js — Research Map renderer =====
   数据只来自 window.KG（data.js ← knowledge_graph.json）。
   不含任何研究知识本体；这里只负责展示。 */

const KG = window.KG;
const NODES = KG.nodes;
const EDGES = KG.edges;

/* ---- 布局：手工定位（x, y 中心坐标），按流程主线排列 ---- */
const LAYOUT = {
  N01: [ 80, 140 ], N02: [ 250, 140 ], N03: [ 420, 140 ], N04: [ 590, 140 ],
  N05: [ 760, 140 ], N06: [ 930, 140 ], N10: [ 1100, 140 ], N11: [ 1270, 140 ],
  N13: [ 1440, 140 ], N14: [ 1270, 330 ], N16: [ 1440, 330 ], N17: [ 1440, 520 ],
  N07: [ 1100, 340 ], N08: [ 1100, 470 ], N09: [ 1100, 600 ],
  N12: [ 800, 360 ], N15: [ 640, 420 ]
};

const NODE_W = 118, NODE_H = 54;

const STATUS_LABEL = {
  supported: "supported · 稳", narrowed: "narrowed · 缩水", rejected: "rejected · 被否",
  retracted: "retracted · 撤回", replaced: "replaced · 改名", frozen: "frozen · 冻结",
  untested: "untested · 未测", open: "open · 开放"
};
const TYPE_LABEL = {
  experiment: "experiment", hypothesis: "hypothesis", mechanism: "mechanism",
  design: "design", failure: "failure", concept: "concept", "open question": "open question"
};
const EDGE_LABEL = {
  leads_to: "leads to", tests: "tests", supports: "supports", rejects: "rejects",
  refines: "refines", replaces: "replaces", depends_on: "depends on",
  connects_to: "connects to", corrects: "corrects"
};

/* ================= rendering helpers ================= */

function nodeById(id) { return NODES.find(n => n.id === id); }
function edgesOf(id) { return EDGES.filter(e => e.from === id || e.to === id); }
function incomingOf(id) { return EDGES.filter(e => e.to === id); }
function outgoingOf(id) { return EDGES.filter(e => e.from === id); }
function edgeKey(e) { return `${e.from}->${e.to}`; }
function href(p) { return (KG.meta.webPathPrefix || "") + p; }

function escapeHtml(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* ================= SVG graph ================= */

const svg = document.getElementById("graph");
const NS = "http://www.w3.org/2000/svg";
let selected = "N16";          // 默认聚焦当前结论
let chainMode = true;          // 默认显示支持链
let activeFilters = new Set(KG.nodeTypes);
let searchText = "";

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

/* 三次贝塞尔：尽量竖直/水平走线，避免穿节点 */
function cubicPath(f, t) {
  const dx = t.x - f.x, dy = t.y - f.y;
  const horizontal = Math.abs(dx) >= Math.abs(dy);
  const bend = Math.min(70, Math.max(24, (horizontal ? Math.abs(dx) : Math.abs(dy)) * 0.28));
  if (horizontal) {
    // 水平主导：控制点在 x 方向外扩
    return `M ${f.x} ${f.y} C ${f.x + bend * (dx >= 0 ? 1 : -1)} ${f.y}, ${t.x - bend * (dx >= 0 ? 1 : -1)} ${t.y}, ${t.x} ${t.y}`;
  }
  return `M ${f.x} ${f.y} C ${f.x} ${f.y + bend * (dy >= 0 ? 1 : -1)}, ${t.x} ${t.y - bend * (dy >= 0 ? 1 : -1)}, ${t.x} ${t.y}`;
}

function renderEdges(visibleSet) {
  const layer = document.createElementNS(NS, "g");
  layer.setAttribute("class", "edge-layer");
  EDGES.forEach(e => {
    const f = nodeById(e.from), t = nodeById(e.to);
    if (!f || !t) return;
    if (!visibleSet.has(e.from) || !visibleSet.has(e.to)) return;
    const fp = LAYOUT[f.id], tp = LAYOUT[t.id];
    const s = { x: fp[0], y: fp[1] }, en = { x: tp[0], y: tp[1] };
    const g = el("g", { class: `edge ${e.type}`, "data-key": edgeKey(e) }, layer);
    el("path", { d: cubicPath(s, en), class: "line", fill: "none", "stroke-width": 1.8 }, g);
    // 箭头：从目标端略缩进，避免顶在节点上
    const ang = Math.atan2(en.y - s.y, en.x - s.x);
    const L = 16;
    const inset = Math.max(NODE_W, NODE_H) / 2 + 5;
    const ax = en.x - Math.cos(ang) * inset;
    const ay = en.y - Math.sin(ang) * inset;
    el("path", {
      d: `M ${ax} ${ay} l ${-L * Math.cos(ang - 0.4)} ${-L * Math.sin(ang - 0.4)}
          M ${ax} ${ay} l ${-L * Math.cos(ang + 0.4)} ${-L * Math.sin(ang + 0.4)}`,
      class: "arrow", fill: "none", "stroke-width": 1.8
    }, g);
    // 标签位置：连线中点，往旁侧偏一点避免压线
    const midX = (s.x + en.x) / 2, midY = (s.y + en.y) / 2;
    el("text", { x: midX, y: midY - 6, class: "edge-label", "text-anchor": "middle" }, g)
      .textContent = EDGE_LABEL[e.type] || e.type;
  });
  svg.prepend(layer);
}

function renderNodes(visibleSet) {
  const layer = document.createElementNS(NS, "g");
  layer.setAttribute("class", "node-layer");
  NODES.forEach(n => {
    const visible = visibleSet.has(n.id);
    const g = el("g", {
      class: `node ${n.status}`,
      "data-id": n.id,
      transform: `translate(${LAYOUT[n.id][0] - NODE_W / 2}, ${LAYOUT[n.id][1] - NODE_H / 2})`,
      opacity: visible ? 1 : 0.12
    }, layer);
    el("rect", { width: NODE_W, height: NODE_H, rx: 10 }, g);
    const mid = NODE_H / 2;
    el("text", { x: 10, y: mid - 7, class: "nid" }, g).textContent = n.id + " · " + (TYPE_LABEL[n.type] || n.type);
    el("text", { x: 10, y: mid + 9, class: "ntitle" }, g).textContent = n.title.length > 12 ? n.title.slice(0, 11) + "…" : n.title;
    el("text", { x: 10, y: mid + 23, class: "badge" }, g).textContent = STATUS_LABEL[n.status] || n.status;
  });
  svg.appendChild(layer);
  layer.querySelectorAll(".node").forEach(g => {
    g.addEventListener("click", () => selectNode(g.dataset.id));
  });
}

/* ---- support-chain computation（从结论反向追溯） ---- */
function supportChain(targetId) {
  const visited = new Set();
  const chainEdges = new Set();
  const stack = [ targetId ];
  while (stack.length) {
    const cur = stack.pop();
    if (visited.has(cur)) continue;
    visited.add(cur);
    incomingOf(cur).forEach(e => {
      if (["supports", "leads_to", "refines", "corrects", "tests", "replaces"].includes(e.type)) {
        chainEdges.add(edgeKey(e));
        stack.push(e.from);
      }
    });
  }
  return { nodes: visited, edges: chainEdges };
}

function applyHighlight() {
  const { nodes, edges } = chainMode ? supportChain(selected) : { nodes: new Set(NODES.map(n => n.id)), edges: new Set() };
  const nodesAll = new Set(NODES.map(n => n.id));
  svg.querySelectorAll(".edge").forEach(g => {
    const key = g.dataset.key;
    const hl = chainMode && edges.has(key);
    const dim = chainMode && !edges.has(key);
    g.classList.toggle("highlight", hl);
    g.classList.toggle("dim", dim);
  });
  svg.querySelectorAll(".node").forEach(g => {
    const id = g.dataset.id;
    g.classList.toggle("dim", chainMode && !nodes.has(id));
    if (chainMode && !nodes.has(id)) g.style.opacity = 0.18;
    else g.style.opacity = 1;
  });
}

function renderGraph() {
  svg.innerHTML = "";
  const visibleSet = new Set();
  NODES.forEach(n => {
    const typeOk = activeFilters.has(n.type);
    const searchOk = !searchText ||
      (n.id + n.title + n.plain + n.answer + n.questions.join(" ") + (n.concepts || []).join(" ")).toLowerCase().includes(searchText);
    if (typeOk && searchOk) visibleSet.add(n.id);
  });
  renderEdges(visibleSet);
  renderNodes(visibleSet);
  applyHighlight();
}

/* ================= legend ================= */

const STATUS_COLORS = {
  supported: "#1f7a44", narrowed: "#1f5fa8", rejected: "#b23b3b", retracted: "#7f1d1d",
  replaced: "#7a3fa0", frozen: "#0e6f6f", untested: "#c07a12", open: "#c07a12"
};
function getStatusColor(s) { return STATUS_COLORS[s] || "#999"; }

function renderLegend() {
  const legend = document.getElementById("legend");
  if (!legend) return;
  legend.innerHTML = "";
  Object.keys(STATUS_LABEL).forEach(s => {
    const span = document.createElement("span");
    span.className = "lg";
    span.innerHTML = `<span class="dot" style="background:${getStatusColor(s)}"></span>${STATUS_LABEL[s] || s}`;
    legend.appendChild(span);
  });
  legend.appendChild(Object.assign(document.createElement("span"), { className: "lg", innerHTML: `<span class="rel">—— rejects / supports / leads-to 线型见图中</span>` }));
}

/* ================= selection ================= */

function selectNode(id) {
  selected = id;
  chainMode = true;
  renderGraph();
  renderDetail(id);
}

/* ================= detail panel ================= */

const detailContent = document.getElementById("detail-content");
const detailEmpty = document.getElementById("detail-empty");

function relRowHTML(e, dir) {
  const otherId = e.from === selected ? e.to : e.from;
  const other = nodeById(otherId);
  return `<div class="relrow ${dir}" data-jump="${escapeHtml(otherId)}">
    <span class="rtype ${e.type}">${EDGE_LABEL[e.type] || e.type}</span>
    → <strong>${escapeHtml(otherId)}</strong> ${escapeHtml(other ? other.title : "")}
    <div class="why">${escapeHtml(e.why || "")}</div>
  </div>`;
}

function renderDetail(id) {
  const n = nodeById(id);
  if (!n) return;
  detailEmpty.hidden = true;
  detailContent.hidden = false;

  detailContent.innerHTML = `
    <div class="kicker">节点 ${n.id} · 实验 ${n.experiment || "—"} · ${n.phase || "—"}</div>
    <h2>${escapeHtml(n.title)}</h2>
    <div class="meta">
      <span class="tag status ${n.status}">${escapeHtml(STATUS_LABEL[n.status] || n.status)}</span>
      <span class="tag">${escapeHtml(TYPE_LABEL[n.type] || n.type)}</span>
    </div>
    <div class="plain">${escapeHtml(n.plain)}</div>
    <section class="questions">
      <h3>这里真正的问题 · ${(n.questions || []).length} 个</h3>
      <ol>${(n.questions || []).map(q => `<li>${escapeHtml(q)}</li>`).join("")}</ol>
    </section>
    <section class="answer">
      <h3>答案（大白话）</h3>
      <p>${escapeHtml(n.answer)}</p>
    </section>
    <section class="changed">
      <h3>这改变了什么理解</h3>
      <div class="ch before"><span class="when">原来</span><div>${escapeHtml(n.changed && n.changed.before || "")}</div></div>
      <div class="ch after"><span class="when">现在</span><div>${escapeHtml(n.changed && n.changed.after || "")}</div></div>
    </section>
    <section class="evidence">
      <h3>证据</h3>
      <ul>
        ${(n.evidence || []).map(ev => `
          <li><a href="${escapeHtml(href(ev.path))}" target="_blank" rel="noopener">${escapeHtml(ev.label)}</a>
          <div class="evpath">${escapeHtml(ev.path)}</div></li>`).join("")}
      </ul>
    </section>
    <section class="relations">
      <h3>关系 × ${(incomingOf(id).length + outgoingOf(id).length)}</h3>
      <div class="rel-in-label">入（谁支撑/导向/否定了它）</div>
      ${incomingOf(id).map(e => relRowHTML(e, "in")).join("")}
      <div class="rel-out-label">出（它导向/支撑/否定了谁）</div>
      ${outgoingOf(id).map(e => relRowHTML(e, "out")).join("")}
    </section>
    ${(n.concepts && n.concepts.length) ? `
    <section class="concepts">
      <h3>概念标签</h3>
      ${n.concepts.map(c => `<span class="chip">${escapeHtml(c)}</span>`).join("")}
    </section>` : ""}
    <section>
      <h3>完整节点笔记（12 节）</h3>
      <p><a href="${escapeHtml(href(n.file))}" target="_blank" rel="noopener">打开 ${escapeHtml(n.file)}</a></p>
    </section>
  `;
  detailContent.querySelectorAll(".relrow").forEach(el => {
    el.addEventListener("click", () => {
      const id2 = el.dataset.jump;
      if (id2) selectNode(id2);
    });
  });
}

/* ================= filters ================= */

function renderFilters() {
  const wrap = document.getElementById("filters");
  wrap.innerHTML = "";
  KG.nodeTypes.forEach(t => {
    const b = document.createElement("button");
    b.className = "filter-chip" + (activeFilters.has(t) ? " on" : "");
    b.textContent = TYPE_LABEL[t] || t;
    b.addEventListener("click", () => {
      if (activeFilters.has(t) && activeFilters.size === 1) return;
      if (activeFilters.has(t)) activeFilters.delete(t); else activeFilters.add(t);
      renderFilters(); renderGraph();
    });
    wrap.appendChild(b);
  });
}

/* ================= search & actions ================= */

document.getElementById("search").addEventListener("input", (ev) => {
  searchText = ev.target.value.trim().toLowerCase();
  renderGraph();
});

document.getElementById("btn-chain").addEventListener("click", () => {
  chainMode = true;
  renderGraph();
  renderDetail(selected);
});

document.getElementById("btn-reset").addEventListener("click", () => {
  searchText = ""; document.getElementById("search").value = "";
  activeFilters = new Set(KG.nodeTypes);
  selected = "N16"; chainMode = true;
  renderFilters(); renderGraph(); renderDetail("N16");
});

/* ================= init ================= */

document.getElementById("headline").textContent = KG.meta.headline;
renderLegend();
renderFilters();
renderGraph();
renderDetail(selected);