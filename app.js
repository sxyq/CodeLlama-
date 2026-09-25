/* Staging dashboard data — final snapshot of UNIFIED-MODEL-STAGING-001 */
const SERVICES = [
  { port: "8000",  name: "vLLM · codellama-13b", badge: "STOPPED", cls: "stop",  meta: "8000 CLOSED · 未恢复" },
  { port: "8010",  name: "Zrald · llama.cpp",    badge: "RUNNING · 动态加载", cls: "ok", meta: "lease manager · ctx 32768 · idle 600s" },
  { port: "11434", name: "Ollama 0.20.7",        badge: "RUNNING · 10 模型", cls: "ok",  meta: "E2E 10/10 PASS · duplicate 已删" },
  { port: "8011",  name: "Image Service",        badge: "RUNNING · lazy load", cls: "ok", meta: "E2E 生成 PASS · idle 600s" },
  { port: "3000",  name: "Open WebUI",           badge: "不被依赖", cls: "off",  meta: "OPEN_WEBUI_REQUIRED = NO" },
];

const DOWNLOADS = [
  {
    title: "Zrald Accuracy GGUF",
    file: "zraldqwen3.8-accuracy.gguf",
    detail: "16,464,440,224 B · SHA256 = LFS oid 匹配 · hf-mirror + clash",
    pct: 100, done: true,
  },
  {
    title: "Qwen-Image-2.1 全量 snapshot",
    file: "29 文件 · 33,134,789,599 B",
    detail: "ModelScope · 7/7 safetensors · 无残留文件",
    pct: 100, done: true,
  },
];

const STORAGE = [
  "/data/vllm/Zrald-Qwen3.8-27B-v2/ — 新增（syy 可写）",
  "/data/vllm/ImageModel/Qwen-Image-2.1/ — 新增",
  "/data/vllm/ 原有 11 模型 — 原样未动",
  "Ollama store /usr/share/ollama/.ollama — 未触碰",
];

const SERVING = [
  "/home/syy/ai-serving/configs/ — vllm snapshot×7 · ollama Modelfile · image yaml · video 占位",
  "/home/syy/ai-serving/services/image/ — server.py · model_manager.py · schemas.py",
  "/home/syy/ai-serving/state/ — models.json · service_state.json",
  "LOCAL 同步：./serving/（无凭据、无权重）",
];

const NOT_DONE = [
  "vLLM YAML/CUDA/Clash/网络/Open WebUI 未改动",
  "Ollama 未升级未重启（仅 rm 已确认损坏的 duplicate）",
  "未重新下载/重量化任何模型 · 凭据未入 Git",
  "GPU lock 双向互斥实测 PASS · LAN 外部 embed 竞争已记录",
  "Git: secret scan PASS → commit 6919738 → push main",
];

const GGUF = [
  ["magic / version", "GGUF v3"],
  ["architecture", "qwen35"],
  ["general.name", "Qwen3.8-27B"],
  ["context_length", "262144（NATIVE_CONTEXT_METADATA）"],
  ["file_type", "15（Q4_K_M 档）"],
  ["tensor_count / kv_count", "866 / 50"],
  ["block_count / embedding", "65 / 5120"],
  ["heads (M/KV)", "24 / 4"],
  ["SHA256", "322e194ff797…39123482（与 LFS 一致）"],
];

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function render() {
  const sc = document.getElementById("service-cards");
  SERVICES.forEach(s => {
    const c = el("div", "card");
    c.appendChild(el("div", "port", s.port));
    c.appendChild(el("div", "name", s.name));
    c.appendChild(el("span", "badge " + s.cls, s.badge));
    c.appendChild(el("div", "meta", s.meta));
    sc.appendChild(c);
  });

  const dc = document.getElementById("download-cards");
  DOWNLOADS.forEach(d => {
    const c = el("div", "card");
    c.appendChild(el("div", "name", d.title));
    c.appendChild(el("div", "port", d.pct + "%"));
    c.appendChild(el("span", "badge " + (d.done ? "ok" : "warn"), d.done ? "VERIFIED" : "DOWNLOADING"));
    c.appendChild(el("div", "meta", d.file + "<br>" + d.detail));
    const p = el("div", "progress" + (d.done ? " done" : ""));
    const bar = el("i");
    bar.style.width = d.pct + "%";
    p.appendChild(bar);
    c.appendChild(p);
    dc.appendChild(c);
  });

  const sl = document.getElementById("storage-list");
  STORAGE.forEach(t => sl.appendChild(el("li", "", t)));
  const svl = document.getElementById("serving-list");
  SERVING.forEach(t => svl.appendChild(el("li", "", t)));
  const nl = document.getElementById("notlist");
  NOT_DONE.forEach(t => nl.appendChild(el("li", "", t)));

  const tb = document.getElementById("gguf-table");
  GGUF.forEach(([k, v]) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("th", "", k));
    tr.appendChild(el("td", "", v));
    tb.appendChild(tr);
  });
}

document.addEventListener("DOMContentLoaded", render);
