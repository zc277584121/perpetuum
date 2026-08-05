const state = {
  status: null,
  selectedProjectId: null,
  project: null,
  selectedFile: "reports/latest.md",
};

const fileLabels = {
  "reports/latest.md": "最新日报",
  "goal.md": "Goal",
  "plan.md": "Task 计划",
  "history.md": "可信历史",
  "inbox.md": "Inbox",
  "questions.md": "Questions",
  "escalations.md": "Escalations",
  "runtime/events.log": "运行日志",
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "请求失败");
  }
  return body;
}

function showToast(message, error = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast visible ${error ? "error" : ""}`;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.className = "toast";
  }, 3200);
}

function statusLabel(value) {
  const labels = {
    idle: "空闲",
    working: "工作中",
    waiting_human: "等待人类",
    control_blocked: "管控阻塞",
    paused: "已暂停",
    unknown: "未知",
  };
  return labels[value] || value || "未知";
}

function renderService() {
  const runner = state.status.runner;
  const service = runner.service || {};
  const alive = Boolean(service.alive);
  document.getElementById("service-dot").className = `status-dot ${alive ? "online" : "offline"}`;
  document.getElementById("service-status").textContent = alive ? "运行中" : "已停止";

  const root = runner.active_root;
  const reporter = runner.active_reporter;
  const details = document.getElementById("service-details");
  details.replaceChildren(
    definition("Root", root ? root.session : "无"),
    definition("Reporter", reporter ? reporter.session : "无"),
    definition("下次检查", runner.next_activation_check_at || "尚未计划"),
  );
}

function definition(term, description) {
  const wrapper = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = description;
  wrapper.append(dt, dd);
  return wrapper;
}

function renderProjects() {
  const list = document.getElementById("project-list");
  list.replaceChildren();
  for (const project of state.status.projects) {
    const button = document.createElement("button");
    button.className = "project-item";
    button.dataset.projectId = project.id;
    if (project.id === state.selectedProjectId) {
      button.classList.add("selected");
    }

    const title = document.createElement("strong");
    title.textContent = project.name;
    const meta = document.createElement("span");
    meta.textContent = project.paused ? "已暂停" : statusLabel(project.status);
    meta.className = `project-state state-${project.paused ? "paused" : project.status}`;
    const path = document.createElement("small");
    path.textContent = project.path;
    button.append(title, meta, path);
    button.addEventListener("click", () => selectProject(project.id));
    list.appendChild(button);
  }
  if (!state.status.projects.length) {
    const empty = document.createElement("p");
    empty.className = "sidebar-empty";
    empty.textContent = "尚未注册项目";
    list.appendChild(empty);
  }
}

function renderProject() {
  if (!state.project) {
    return;
  }
  const summary = state.project.summary;
  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("project-view").classList.remove("hidden");
  document.getElementById("project-controls").classList.remove("hidden");
  document.getElementById("project-name").textContent = summary.name;
  document.getElementById("project-path").textContent = summary.path;
  const windowInput = document.getElementById("window-text");
  if (document.activeElement !== windowInput) {
    windowInput.value = (summary.windows || []).join(", ");
  }
  const pauseButton = document.getElementById("pause-button");
  pauseButton.textContent = summary.paused ? "恢复" : "暂停";
  pauseButton.dataset.action = summary.paused ? "resume" : "pause";

  const metrics = document.getElementById("metrics");
  metrics.replaceChildren(
    metric("项目状态", summary.paused ? "已暂停" : statusLabel(summary.status)),
    metric("当前 Task", summary.current_task || "无"),
    metric("最近活动", summary.last_activity_at || "暂无"),
    metric("时间窗口", (summary.windows || []).join("，") || "未配置"),
  );

  const tabs = document.getElementById("document-tabs");
  tabs.replaceChildren();
  for (const name of Object.keys(fileLabels)) {
    const button = document.createElement("button");
    button.textContent = fileLabels[name];
    button.dataset.file = name;
    if (name === state.selectedFile) {
      button.classList.add("selected");
    }
    button.addEventListener("click", () => {
      state.selectedFile = name;
      renderProject();
    });
    tabs.appendChild(button);
  }
  document.getElementById("document-content").textContent =
    state.project.files[state.selectedFile] || "暂无内容。";
}

function metric(label, value) {
  const card = document.createElement("article");
  const heading = document.createElement("span");
  const content = document.createElement("strong");
  heading.textContent = label;
  content.textContent = value;
  card.append(heading, content);
  return card;
}

async function loadStatus(keepSelection = true) {
  try {
    state.status = await request("/api/status");
    if (!keepSelection || !state.status.projects.some(project => project.id === state.selectedProjectId)) {
      state.selectedProjectId = state.status.projects[0]?.id || null;
    }
    renderService();
    renderProjects();
    if (state.selectedProjectId) {
      await loadProject(state.selectedProjectId);
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadProject(projectId) {
  state.project = await request(`/api/projects/${encodeURIComponent(projectId)}`);
  renderProject();
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  renderProjects();
  try {
    await loadProject(projectId);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function postProject(action, body) {
  if (!state.selectedProjectId) {
    return;
  }
  await request(
    `/api/projects/${encodeURIComponent(state.selectedProjectId)}/${action}`,
    {method: "POST", body: JSON.stringify(body)},
  );
  await loadStatus();
}

document.getElementById("refresh-button").addEventListener("click", () => loadStatus());

document.getElementById("project-controls").addEventListener("click", async event => {
  const action = event.target.dataset.action;
  if (!action) {
    return;
  }
  try {
    await postProject("control", {action});
    showToast(action === "run" ? "已请求立即运行" : "项目状态已更新");
  } catch (error) {
    showToast(error.message, true);
  }
});

document.getElementById("send-inbox").addEventListener("click", async () => {
  const input = document.getElementById("inbox-text");
  try {
    await postProject("inbox", {text: input.value});
    input.value = "";
    showToast("指令已写入 Inbox");
  } catch (error) {
    showToast(error.message, true);
  }
});

document.getElementById("send-response").addEventListener("click", async () => {
  const input = document.getElementById("response-text");
  const channel = document.getElementById("response-channel").value;
  try {
    await postProject("response", {channel, text: input.value});
    input.value = "";
    showToast("回复已追加");
  } catch (error) {
    showToast(error.message, true);
  }
});

document.getElementById("save-windows").addEventListener("click", async () => {
  const value = document.getElementById("window-text").value;
  const windows = value.split(",").map(item => item.trim()).filter(Boolean);
  try {
    await postProject("control", {action: "window", windows});
    showToast("时间窗口已更新");
  } catch (error) {
    showToast(error.message, true);
  }
});

loadStatus(false);
window.setInterval(() => loadStatus(), 15000);
