"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

let currentChart = null;
let currentInterp = null;
let currentProfileId = null;

/* ---------- 工具 ---------- */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

let toastTimer = null;
function toast(msg, type = "") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 2600);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  let data;
  try { data = await res.json(); } catch { data = { ok: false, error: "响应解析失败" }; }
  if (!res.ok || data.ok === false) throw new Error(data.error || ("请求失败 " + res.status));
  return data;
}

/* ---------- 表单 ---------- */
function getBirth() {
  const f = $("#birth-form");
  const v = (n) => f.elements[n].value;
  const c = (n) => f.elements[n].checked;
  const lon = v("longitude").trim();
  return {
    name: v("name").trim() || "未命名",
    gender: parseInt(v("gender"), 10),
    calendar: v("calendar"),
    year: parseInt(v("year"), 10),
    month: parseInt(v("month"), 10),
    day: parseInt(v("day"), 10),
    hour: parseInt(v("hour"), 10),
    minute: parseInt(v("minute"), 10),
    is_leap: c("is_leap"),
    use_true_solar: c("use_true_solar"),
    longitude: lon === "" ? null : parseFloat(lon),
    sect: parseInt(v("sect"), 10),
  };
}

function fillForm(b) {
  const f = $("#birth-form");
  f.elements["name"].value = b.name || "";
  f.elements["gender"].value = String(b.gender ?? 1);
  f.elements["calendar"].value = b.calendar || "solar";
  f.elements["year"].value = b.year;
  f.elements["month"].value = b.month;
  f.elements["day"].value = b.day;
  f.elements["hour"].value = b.hour;
  f.elements["minute"].value = b.minute ?? 0;
  f.elements["is_leap"].checked = !!b.is_leap;
  f.elements["use_true_solar"].checked = !!b.use_true_solar;
  f.elements["longitude"].value = b.longitude ?? "";
  f.elements["sect"].value = String(b.sect ?? 2);
  toggleLeap();
}

function toggleLeap() {
  const isLunar = $("#calendar").value === "lunar";
  $("#leap-wrap").classList.toggle("hidden", !isLunar);
}

/* ---------- 渲染：四柱 ---------- */
function renderPillars(ch) {
  const order = [["year", "年柱"], ["month", "月柱"], ["day", "日柱"], ["time", "时柱"]];
  const p = ch.pillars;
  const row = (label, fn) =>
    `<tr><td class="label-col">${label}</td>` +
    order.map(([k]) => `<td>${fn(p[k])}</td>`).join("") + "</tr>";

  const rows = [
    row("十神", (q) => esc(q.shiShenGan || "日主")),
    row("天干", (q) => `<span class="gz gan">${esc(q.gan)}</span>`),
    row("地支", (q) => `<span class="gz zhi">${esc(q.zhi)}</span>`),
    row("藏干", (q) => esc(q.hideGan.join(" ")) || "—"),
    row("藏干十神", (q) => esc(q.hideShiShen.join(" ")) || "—"),
    row("纳音", (q) => esc(q.naYin)),
    row("空亡", (q) => esc(q.xunKong)),
  ];
  return `<div class="block">
    <h3>四柱命盘</h3>
    <table class="pillar-table"><thead><tr><th></th>${order.map((o) => `<th>${o[1]}</th>`).join("")}</tr></thead>
    <tbody>${rows.join("")}</tbody></table>
  </div>`;
}

/* ---------- 渲染：基本信息 ---------- */
function renderInfo(ch) {
  const items = [
    ["公历", ch.solar.datetime],
    ["农历", ch.lunarText],
    ["生肖", ch.shengXiao],
    ["时辰", ch.shiChen],
    ["日主", `${ch.dayMaster.gan}（${ch.dayMaster.yinYang}${ch.dayMaster.wuXing}）`],
    ["胎元", ch.taiYuan], ["命宫", ch.mingGong], ["身宫", ch.shenGong],
    ["起运", ch.qiyun.text],
  ];
  if (ch.trueSolar) {
    items.push(["真太阳时", `${ch.trueSolar.trueSolarTime}（偏移 ${ch.trueSolar.offsetMinutes} 分）`]);
  }
  if (ch.jieqi && ch.jieqi.monthJie) {
    items.push(["月令节气", `${ch.jieqi.monthJie.name} ${ch.jieqi.monthJie.time}`]);
  }
  if (ch.jieqi && ch.jieqi.liChun) items.push(["立春", ch.jieqi.liChun]);
  const html = items.map(([k, v]) =>
    `<div><div class="k">${esc(k)}</div><div>${esc(v)}</div></div>`).join("");
  return `<div class="block"><h3>基本信息</h3><div class="info-grid">${html}</div></div>`;
}

/* ---------- 渲染：五行 ---------- */
function renderWuxing(ch) {
  const wx = ch.wuXing;
  const rows = ["木", "火", "土", "金", "水"].map((k) => {
    const pct = wx.percent[k];
    return `<div class="wx-row">
      <span class="wx-name">${k}</span>
      <span class="wx-bar"><span class="wx-fill wx-${k}" style="width:${Math.min(100, pct)}%"></span></span>
      <span class="wx-val">${pct}% / ${wx.score[k]}</span>
    </div>`;
  }).join("");
  const miss = wx.missing.length
    ? `<div class="muted small" style="margin-top:8px">五行本气缺失：${esc(wx.missing.join("、"))}</div>`
    : `<div class="muted small" style="margin-top:8px">五行本气俱全</div>`;
  return `<div class="block"><h3>五行力量分布</h3>${rows}${miss}</div>`;
}

/* ---------- 渲染：大运 ---------- */
function renderDayun(ch) {
  const items = ch.dayun.map((d, i) =>
    `<div class="dayun-item ${d.isCurrent ? "active" : ""}" data-idx="${i}">
      <div class="gz"><span class="gan">${esc(d.gan)}</span><span class="zhi">${esc(d.zhi)}</span></div>
      <div class="ss">${esc(d.shiShenGan)}</div>
      <div class="age">${d.startAge}–${d.endAge}岁</div>
      <div class="age">${d.startYear}–${d.endYear}</div>
    </div>`).join("");
  return `<div class="block">
    <h3>大运（点击查看对应流年）</h3>
    <div class="dayun-scroll" id="dayun-scroll">${items}</div>
    <div id="liunian-box" style="margin-top:12px"></div>
  </div>`;
}

function showLiunian(idx) {
  const d = currentChart.dayun[idx];
  const thisYear = new Date().getFullYear();
  const chips = d.liuNian.map((n) =>
    `<span class="${n.year === thisYear ? "now" : ""}">${n.year} ${esc(n.ganZhi)}</span>`).join("");
  $("#liunian-box").innerHTML =
    `<h3>${esc(d.ganZhi)} 大运流年（${d.startYear}–${d.endYear}）</h3>
     <div class="liunian-list">${chips}</div>`;
}

/* ---------- 渲染：规则解读 ---------- */
function renderInterpret(interp) {
  const secs = interp.sections.map((s) =>
    `<div class="sec-title">${esc(s.title)}</div>
     <ul>${s.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`).join("");
  return `<div class="block interp"><h3>规则引擎解读</h3>${secs}</div>`;
}

/* ---------- 渲染：AI ---------- */
function renderAI() {
  return `<div class="block ai-area">
    <h3>AI 深度解读（可选）</h3>
    <p class="muted small" id="ai-status">未启用。点击右上角「AI 设置」配置接口后可用；
      启用前你的数据不会离开本机。</p>
    <textarea id="ai-question" placeholder="可补充想问的重点，例如：适合从事什么行业？近年事业运势如何？（留空则做全面解读）"></textarea>
    <div class="actions" style="margin-top:8px">
      <button id="btn-ai" class="primary">AI 解读</button>
    </div>
    <div id="ai-output" class="ai-output hidden"></div>
  </div>`;
}

/* ---------- 主渲染 ---------- */
function render(ch, interp, profileId) {
  currentChart = ch;
  currentInterp = interp;
  currentProfileId = profileId ?? null;
  const cur = ch.dayun.findIndex((d) => d.isCurrent);
  $("#empty-state").classList.add("hidden");
  const r = $("#result");
  r.classList.remove("hidden");
  r.innerHTML =
    `<div class="result-head">
      <div><span class="name">${esc(ch.input.name)}</span>
        <span class="muted"> · ${esc(ch.input.genderText)} · ${esc(ch.solar.datetime)}</span></div>
      <div class="meta">${esc(interp.summary)}</div>
    </div>` +
    renderPillars(ch) + renderInfo(ch) + renderWuxing(ch) +
    renderDayun(ch) + renderInterpret(interp) + renderAI();

  $$("#dayun-scroll .dayun-item").forEach((el) => {
    el.addEventListener("click", () => {
      $$("#dayun-scroll .dayun-item").forEach((x) => x.classList.remove("active"));
      el.classList.add("active");
      showLiunian(parseInt(el.dataset.idx, 10));
    });
  });
  if (cur >= 0) showLiunian(cur);

  $("#btn-ai").addEventListener("click", askAI);
  refreshAIStatus();
}

/* ---------- 档案 ---------- */
async function loadProfiles() {
  try {
    const { profiles } = await api("/api/profiles");
    const ul = $("#profile-list");
    if (!profiles.length) {
      ul.innerHTML = `<li class="muted small" style="cursor:default;border-style:dashed">暂无档案</li>`;
      return;
    }
    ul.innerHTML = profiles.map((p) =>
      `<li data-id="${p.id}">
        <div>
          <div class="pname">${esc(p.name)} · ${p.gender === 1 ? "男" : "女"}</div>
          <div class="pmeta">${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}
            ${String(p.hour).padStart(2, "0")}:${String(p.minute ?? 0).padStart(2, "0")}
            · ${p.calendar === "lunar" ? "农历" : "公历"}</div>
        </div>
        <button class="del" data-del="${p.id}" title="删除">删除</button>
      </li>`).join("");

    $$("#profile-list li[data-id]").forEach((li) => {
      li.addEventListener("click", (e) => {
        if (e.target.dataset.del) return;
        loadProfile(parseInt(li.dataset.id, 10), profiles);
      });
    });
    $$("#profile-list .del").forEach((b) => {
      b.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm("确定删除该档案？（仅影响本机数据）")) return;
        await api("/api/profiles/" + b.dataset.del, { method: "DELETE" });
        toast("已删除", "ok");
        loadProfiles();
      });
    });
  } catch (e) { toast(e.message, "err"); }
}

async function loadProfile(id, profiles) {
  const p = profiles.find((x) => x.id === id);
  if (!p) return;
  fillForm(p);
  await compute(true);
  toast("已载入档案", "ok");
}

/* ---------- 排盘 ---------- */
async function compute(fromProfile) {
  const birth = getBirth();
  const res = await api("/api/chart", { method: "POST", body: JSON.stringify({ birth }) });
  render(res.chart, res.interpretation, fromProfile ? currentProfileId : null);
  $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------- AI ---------- */
async function refreshAIStatus() {
  try {
    const { ai } = await api("/api/settings");
    const el = $("#ai-status");
    if (!el) return;
    if (ai.enabled && ai.has_key && ai.model && ai.base_url) {
      el.textContent = `已启用：${ai.model} @ ${ai.base_url}（密钥 ${ai.api_key}）`;
      el.style.color = "var(--green)";
    } else if (ai.enabled) {
      el.textContent = "已开启但配置不完整，请在「AI 设置」中补全 base_url / model / key。";
      el.style.color = "var(--accent)";
    } else {
      el.textContent = "未启用。点击右上角「AI 设置」配置接口后可用；启用前你的数据不会离开本机。";
      el.style.color = "";
    }
  } catch { /* 忽略 */ }
}

async function askAI() {
  const btn = $("#btn-ai");
  const out = $("#ai-output");
  const q = $("#ai-question").value.trim();
  btn.disabled = true;
  const old = btn.textContent;
  btn.innerHTML = `<span class="spinner"></span>解读中…`;
  out.classList.remove("hidden");
  out.innerHTML = `<span class="muted">正在请求 AI 接口（此操作会将当前命盘发送到你所配置的服务）…</span>`;
  try {
    const res = await api("/api/ai", {
      method: "POST",
      body: JSON.stringify({ chart: currentChart, interpretation: currentInterp, question: q }),
    });
    out.innerHTML = mdToHtml(res.text);
  } catch (e) {
    out.innerHTML = `<span style="color:var(--red)">${esc(e.message)}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

/* 极简 Markdown 渲染 */
function mdToHtml(md) {
  const lines = esc(md).split(/\r?\n/);
  let html = "", inList = false;
  const inline = (s) => s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
  for (const raw of lines) {
    const line = raw.trim();
    if (/^[-*]\s+/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += "<li>" + inline(line.replace(/^[-*]\s+/, "")) + "</li>";
      continue;
    }
    if (inList) { html += "</ul>"; inList = false; }
    if (/^###\s/.test(line)) html += "<h3>" + inline(line.slice(4)) + "</h3>";
    else if (/^##\s/.test(line)) html += "<h2>" + inline(line.slice(3)) + "</h2>";
    else if (/^#\s/.test(line)) html += "<h1>" + inline(line.slice(2)) + "</h1>";
    else if (line === "") html += "";
    else html += "<p>" + inline(line) + "</p>";
  }
  if (inList) html += "</ul>";
  return html;
}

/* ---------- 设置弹窗 ---------- */
async function openSettings() {
  try {
    const { ai } = await api("/api/settings");
    $("#ai-enabled").checked = !!ai.enabled;
    $("#ai-base").value = ai.base_url || "";
    $("#ai-key").value = ai.api_key || "";
    $("#ai-temp").value = ai.temperature ?? 0.7;
    $("#ai-model").value = ai.model || "";
  } catch (e) { toast(e.message, "err"); }
  $("#settings-modal").classList.remove("hidden");
}

async function saveSettings() {
  try {
    const body = { ai: {
      enabled: $("#ai-enabled").checked,
      base_url: $("#ai-base").value.trim(),
      api_key: $("#ai-key").value.trim(),
      model: $("#ai-model").value.trim(),
      temperature: parseFloat($("#ai-temp").value) || 0.7,
    } };
    await api("/api/settings", { method: "POST", body: JSON.stringify(body) });
    toast("AI 设置已保存到本机", "ok");
    $("#settings-modal").classList.add("hidden");
    refreshAIStatus();
  } catch (e) { toast(e.message, "err"); }
}

/* ---------- 绑定 ---------- */
function init() {
  $("#calendar").addEventListener("change", toggleLeap);
  $("#birth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await compute(false); } catch (err) { toast(err.message, "err"); }
  });
  $("#btn-save").addEventListener("click", async () => {
    try {
      const birth = getBirth();
      const res = await api("/api/profiles", { method: "POST", body: JSON.stringify({ birth }) });
      toast("已保存到本机（id=" + res.id + "）", "ok");
      loadProfiles();
    } catch (e) { toast(e.message, "err"); }
  });
  $("#btn-settings").addEventListener("click", openSettings);
  $("#btn-save-ai").addEventListener("click", saveSettings);
  $("#btn-close-ai").addEventListener("click", () => $("#settings-modal").classList.add("hidden"));
  $("#settings-modal").addEventListener("click", (e) => {
    if (e.target.id === "settings-modal") e.target.classList.add("hidden");
  });
  toggleLeap();
  loadProfiles();
  compute(false).catch(() => {});
}

document.addEventListener("DOMContentLoaded", init);