"use strict";
const $ = (id) => document.getElementById(id);
const API = location.protocol.startsWith("http") && location.port === "8000" ? "" : "http://localhost:8000";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const badge = (v) => `<span class="badge b-${esc(v)}">${esc(v)}</span>`;
const SAMPLE_CV = `Ivan Petrov
ivan.petrov@example.com +380 50 123 4567 Kyiv, Ukraine
Backend developer with 5 years of experience building Python APIs with FastAPI and PostgreSQL
Built REST services in Python and Docker for an e-commerce platform serving 200000 users
Reduced API response time by 40 percent by adding Redis caching
Set up CI pipelines in GitLab CI for automated tests and deployments
Mentored 2 junior developers and ran weekly code reviews
Skills: Python, SQL, Docker, Git, Linux, FastAPI, PostgreSQL, Redis
Bachelor degree in Computer Science, KPI University`;
const SAMPLE_JOB = `Senior Python Backend Developer
3+ years of Python experience
Experience with FastAPI or Django
Docker and CI/CD pipelines
Kubernetes experience
Strong SQL and PostgreSQL knowledge
AWS is a plus
Must be located in Ukraine or the EU`;
let state = { data: null, urls: [], tab: "overview" };

async function init() {
  try {
    const cfg = await (await fetch(API + "/demo/config")).json();
    for (const o of $("provider").options) {
      const p = cfg.providers[o.value];
      if (p && ["gemini", "deepseek", "openrouter"].includes(o.value)) o.text += p.ready ? " ✓ ключ в .env" : " (нужен ключ)";
    }
    if (cfg.default && cfg.providers[cfg.default]?.ready) $("provider").value = cfg.default;
  } catch { $("status").textContent = "⚠ Бэкенд недоступен. Запустите: make demo"; $("status").className = "err"; }
  toggle();
}
function toggle() {
  const ext = ["gemini", "deepseek", "openrouter"].includes($("provider").value);
  $("consentRow").style.display = ext ? "flex" : "none";
}
function fill() { $("cv").value = SAMPLE_CV; $("job").value = SAMPLE_JOB; }

async function run(forceFake) {
  if (forceFake) fill();
  const body = {
    cv_text: $("cv").value, job_text: $("job").value, company_hook: $("hook").value,
    mode: $("mode").value, provider: forceFake ? "fake" : $("provider").value, model: $("model").value,
    api_key: $("key").value, consent: $("consent").checked, work_authorization: $("auth").value,
    location: $("loc").value, max_pages: +$("pages").value, effort: $("effort").value,
  };
  $("run").disabled = $("full").disabled = true;
  $("status").className = ""; $("status").textContent = "⏳ Работаю… (с LLM может занять 30–90 с)";
  try {
    const r = await fetch(API + "/demo/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await r.json();
    if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail));
    state.data = d; $("status").textContent = "✅ Готово";
    state.urls.forEach(URL.revokeObjectURL); state.urls = [];
    $("out").classList.remove("hidden"); state.tab = "overview"; render();
    $("out").scrollIntoView({ behavior: "smooth" });
  } catch (e) { $("status").className = "err"; $("status").textContent = "❌ " + e.message; }
  $("run").disabled = $("full").disabled = false;
}

const TABS = [["overview", "Обзор"], ["reqs", "Требования"], ["roles", "Роли"], ["gaps", "Пробелы и вопросы"],
  ["resume", "Резюме"], ["letter", "Письмо"], ["pdf", "PDF"], ["json", "JSON"], ["log", "Лог LLM"]];
function render() {
  $("tabs").innerHTML = TABS.map(([k, n]) => `<button data-t="${k}" class="${k === state.tab ? "on" : ""}">${n}</button>`).join("");
  $("tabs").querySelectorAll("button").forEach((b) => (b.onclick = () => { state.tab = b.dataset.t; render(); }));
  $("pane").innerHTML = VIEWS[state.tab](state.data);
}
const blobUrl = (b64, type) => {
  const bin = atob(b64), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const u = URL.createObjectURL(new Blob([u8], { type })); state.urls.push(u); return u;
};
const warn = (d) => (d.warnings.length ? `<div class="item"><b>Замечания:</b><br>${d.warnings.map(esc).join("<br>")}</div>` : "");
const VIEWS = {
  overview: (d) => `<div class="big-bucket">Соответствие: ${badge(d.triage.bucket)}</div><p>${esc(d.triage.explanation)}</p>
    ${d.triage.hard_constraint_failure_reasons.map((r) => `<div class="item">🚫 ${esc(r)}</div>`).join("")}
    <p><b>${esc(d.candidate.name)}</b> · фактов из CV: ${d.facts.length} · требований: ${d.requirements.length} · страниц в PDF: ${d.resume_pages} · модель: ${esc(d.provider)}</p>${warn(d)}`,
  reqs: (d) => {
    const f = Object.fromEntries(d.triage.findings.map((x) => [x.requirement_id, x]));
    return d.requirements.map((r) => { const x = f[r.id];
      return `<div class="item">${badge(r.kind)} ${x ? badge(x.category) : ""} ${esc(r.text)}
      ${x ? `<small>${esc(x.rationale)}${x.fact_ids.length ? " · факты: " + x.fact_ids.map(esc).join(", ") : ""}</small>` : ""}</div>`; }).join("");
  },
  roles: (d) => d.roles.suggestions.length ? d.roles.suggestions.map((s) => `<div class="item"><b>${esc(s.role_id)}</b> · уровень ${s.level}
    <br>${esc(s.why)}<small>пробелы: ${s.gap_skill_ids.map(esc).join(", ") || "—"}</small></div>`).join("") + warn({ warnings: d.roles.warnings || [] }) : "<p>Подходящих направлений не найдено.</p>",
  gaps: (d) => (d.gaps.clarification_questions.map((q) => `<div class="item">❓ ${esc(q.question)}</div>`).join("") || "<p>Уточняющих вопросов нет.</p>") +
    (d.transferable.length ? "<h3>Переносимые навыки</h3>" + d.transferable.map((t) => `<div class="item">${badge(t.category)} <b>${esc(t.competence)}</b><small>${esc(t.rationale)}</small></div>`).join("") : ""),
  resume: (d) => `<h3>Изменения формулировок</h3>${d.changes.map((c) => `<div class="item">${badge(c.status)} ${c.status === "applied" ? `<del>${esc(c.before)}</del><br><ins>${esc(c.after)}</ins>` : esc(c.before)}
    <small>${esc(c.reason)}</small></div>`).join("") || "<p>Нет.</p>"}<h3>Итоговое резюме (Markdown)</h3><div class="doc">${esc(d.resume_markdown)}</div>`,
  letter: (d) => `<div class="doc">${esc(d.cover_letter.cover_letter)}</div>` +
    d.cover_letter.clarification_questions.map((q) => `<div class="item">❓ ${esc(q.question)}</div>`).join(""),
  pdf: (d) => { const a = blobUrl(d.resume_pdf_b64, "application/pdf"), b = blobUrl(d.cover_letter_pdf_b64, "application/pdf"),
    m = URL.createObjectURL(new Blob([d.resume_markdown], { type: "text/markdown" })); state.urls.push(m);
    return `<a class="dl" href="${a}" download="resume.pdf">⬇ Резюме PDF</a><a class="dl" href="${b}" download="cover_letter.pdf">⬇ Письмо PDF</a><a class="dl" href="${m}" download="resume.md">⬇ Резюме .md</a><iframe src="${a}"></iframe>`; },
  json: (d) => { const { resume_pdf_b64, cover_letter_pdf_b64, ...rest } = d; return `<pre>${esc(JSON.stringify(rest, null, 2))}</pre>`; },
  log: (d) => d.trace.map((t) => `<div class="item">${badge(t.ok ? "ok" : "blocked")} <b>${esc(t.task)}</b> · ${t.ms} мс${t.error ? `<small>${esc(t.error)}</small>` : ""}</div>`).join("") || "<p>Нет вызовов.</p>",
};
$("sample").onclick = fill; $("clear").onclick = () => { $("cv").value = $("job").value = ""; };
$("provider").onchange = toggle; $("run").onclick = () => run(false); $("full").onclick = () => run(true);
init();
