const $ = (sel) => document.querySelector(sel);

// ---------------------------------------------------------------- tabs
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "history") loadHistory();
    if (btn.dataset.tab === "files") loadFiles();
  });
});

// ------------------------------------------------------------- status
async function pollStatus() {
  try {
    const s = await (await fetch("/api/status")).json();
    let flags = "";
    if (s.paused) flags += " ⏸ PAUSED";
    if (s.stop_requested) flags += " ⏹ STOPPING AFTER THIS CYCLE";
    $("#header-flags").textContent = `${s.task_name}${flags}`;
    $("#header-line1").textContent =
      `running for ${s.elapsed} · ~${s.work_done_estimate} piece(s) of work done · ${s.done} logged / ${s.pending} queued`;

    if (s.trigger_type === "schedule" && s.iter_max) {
      const pct = Math.round((100 * (s.iter_current || 0)) / s.iter_max);
      $("#progress-bar").style.width = pct + "%";
      const eta = s.next_check_in_s != null ? `  ·  next check in ~${s.next_check_in_s}s` : "";
      $("#progress-line2").textContent = `round ${s.iter_current}/${s.iter_max}${eta}`;
    } else if (s.trigger_type === "conditional" || s.trigger_type === "webhook") {
      $("#progress-bar").style.width = "0%";
      const kind = s.trigger_type === "conditional" ? "checked for changes" : "reacted to events";
      $("#progress-line2").textContent = `${kind} ${s.cycles_seen} time(s) so far — event-driven, no fixed total`;
    } else {
      $("#progress-line2").textContent = "warming up…";
    }

    $("#btn-pause").textContent = s.paused ? "▶ Resume" : "⏸ Pause";
    $("#btn-pause").classList.toggle("active", s.paused);
  } catch (e) {
    $("#header-flags").textContent = "(lost contact with dashboard server)";
  }
}

// -------------------------------------------------------------- done
async function pollDone() {
  const items = await (await fetch("/api/done?n=15")).json();
  const list = $("#done-list");
  list.innerHTML = "";
  [...items].reverse().forEach((d) => {
    const li = document.createElement("li");
    li.textContent = `[${d.dim}] ${d.title} — ${d.status}`;
    list.appendChild(li);
  });
  if (!items.length) list.innerHTML = "<li class='dim'>(nothing finished yet)</li>";
}

// ------------------------------------------------------- escalations
async function pollEscalations() {
  const items = await (await fetch("/api/escalations")).json();
  $("#needs-count").textContent = items.length;
  $(".panel.needs").classList.toggle("alert", items.length > 0);
  const wrap = $("#needs-list");
  wrap.innerHTML = "";
  if (!items.length) {
    wrap.innerHTML = "<span class='dim'>(nothing waiting on you)</span>";
    return;
  }
  items.forEach((esc) => {
    const div = document.createElement("div");
    div.className = "escalation";
    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `[${esc.index}] ${esc.title}`;
    div.appendChild(title);

    esc.options.forEach((opt) => {
      const b = document.createElement("button");
      b.className = "opt-btn";
      b.textContent = opt;
      b.onclick = () => resolveEscalation(esc.index, opt);
      div.appendChild(b);
    });

    const ff = document.createElement("div");
    ff.className = "freeform";
    const inp = document.createElement("input");
    inp.type = "text";
    inp.placeholder = esc.options.length ? "…or type your own answer" : "type your answer";
    const send = document.createElement("button");
    send.textContent = "Send";
    send.onclick = () => {
      if (inp.value.trim()) resolveEscalation(esc.index, inp.value.trim());
    };
    ff.appendChild(inp);
    ff.appendChild(send);
    div.appendChild(ff);

    wrap.appendChild(div);
  });
}

async function resolveEscalation(index, answer) {
  await fetch("/api/escalations/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ index, answer }),
  });
  pollEscalations();
  pollDone();
}

// ----------------------------------------------------------- sessions
let currentSession = null;
let userScrolledUp = false;

async function loadSessions() {
  const info = await (await fetch("/api/sessions")).json();
  const picker = $("#session-picker");
  const prev = picker.value;
  picker.innerHTML = "";
  const preferred = info.layer2_default;
  info.sessions.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s === info.layer2_default ? s + "  (Layer 2)" : s;
    picker.appendChild(opt);
  });
  picker.value = info.sessions.includes(prev) ? prev : (info.sessions.includes(preferred) ? preferred : info.sessions[0]);
  currentSession = picker.value;
}

$("#session-picker").addEventListener("change", (e) => {
  currentSession = e.target.value;
  userScrolledUp = false;
});

let lastPaneText = "";
async function pollPane() {
  if (!currentSession) return;
  try {
    const r = await (await fetch(`/api/pane?session=${encodeURIComponent(currentSession)}&lines=400`)).json();
    const view = $("#pane-view");
    const atBottom = view.scrollTop + view.clientHeight >= view.scrollHeight - 20;
    userScrolledUp = !atBottom && lastPaneText !== "";
    if (r.text !== lastPaneText) {
      view.textContent = r.text;
      lastPaneText = r.text;
      if (!userScrolledUp) view.scrollTop = view.scrollHeight;
    }
    $("#quiet-indicator").textContent = "";
  } catch (e) {
    $("#quiet-indicator").textContent = "(session gone)";
  }
}

// ----------------------------------------------------------- controls
$("#btn-pause").addEventListener("click", async () => {
  await fetch("/api/pause", { method: "POST" });
  pollStatus();
});
$("#btn-stop").addEventListener("click", async () => {
  if (confirm("Stop after the current cycle finishes?")) {
    await fetch("/api/stop", { method: "POST" });
    pollStatus();
  }
});
$("#inbox-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("#inbox-text").value.trim();
  if (!text) return;
  await fetch("/api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  $("#inbox-text").value = "";
});

// ------------------------------------------------------------- history
let historyLoaded = false;
async function loadHistory() {
  if (historyLoaded) return;
  const h = await (await fetch("/api/history")).json();
  $("#project-summary").textContent = h.project_summary || "(no .memsearch/PROJECT.md found)";
  const wrap = $("#history-days");
  wrap.innerHTML = "";
  if (!h.days.length) {
    wrap.innerHTML = "<p class='dim'>(no .memsearch/memory/*.md found — memsearch may not be configured for this project)</p>";
  }
  h.days.forEach((day) => {
    const panel = document.createElement("div");
    panel.className = "panel";
    panel.innerHTML = `<div class="panel-title">🗓 ${day.date}</div><pre class="history-block"></pre>`;
    panel.querySelector("pre").textContent = day.content;
    wrap.appendChild(panel);
  });
  historyLoaded = true;
}

// ---------------------------------------------------------------- files
let filesLoaded = false;
async function loadFiles() {
  if (filesLoaded) return;
  const paths = await (await fetch("/api/files")).json();
  const list = $("#file-list");
  list.innerHTML = "";
  paths.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = p;
    li.onclick = () => openFile(p, li);
    list.appendChild(li);
  });
  filesLoaded = true;
  // Nice default: open 1_explore.md or the first prompt-ish file if present.
  const preferred = paths.find((p) => p.includes("1_explore")) || paths[0];
  if (preferred) {
    const li = [...list.children].find((el) => el.textContent === preferred);
    if (li) openFile(preferred, li);
  }
}

async function openFile(path, liEl) {
  document.querySelectorAll("#file-list li").forEach((el) => el.classList.remove("active"));
  liEl.classList.add("active");
  const r = await (await fetch(`/api/file?path=${encodeURIComponent(path)}`)).json();
  $("#file-content").textContent = r.content ?? "";
}

// --------------------------------------------------------------- boot
loadSessions();
pollStatus();
pollDone();
pollEscalations();
setInterval(pollStatus, 2000);
setInterval(pollDone, 4000);
setInterval(pollEscalations, 3000);
setInterval(loadSessions, 8000);
setInterval(pollPane, 1000);
