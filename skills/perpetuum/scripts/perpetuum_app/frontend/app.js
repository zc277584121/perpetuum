const state = {
  status: null,
  selectedProjectId: null,
  project: null,
  selectedFile: "goal.md",
  selectedStory: null,
};

const documents = {
  "goal.md": {label: "Goal", surface: "业务面", access: "只读"},
  "history.md": {label: "可信历史", surface: "业务面", access: "只读"},
  "inbox.md": {label: "完整 Inbox", surface: "业务面", access: "只读浏览"},
  "questions.md": {label: "完整 Questions", surface: "业务面", access: "只读浏览"},
  "escalations.md": {label: "完整 Escalations", surface: "管控面", access: "只读浏览"},
  "reports/latest.md": {label: "最新日报", surface: "业务面", access: "只读"},
  "runtime/events.log": {label: "运行事件", surface: "管控面", access: "只读"},
};

const storyColumns = [
  {status: "candidate", label: "候选", description: "方向成立，但范围或验收仍需整理"},
  {status: "ready", label: "待开始", description: "边界清楚，可以进入执行"},
  {status: "in_progress", label: "进行中", description: "当前正在推进的 Story"},
  {status: "waiting", label: "等待", description: "等待人类、管控处理或外部条件"},
  {status: "done", label: "已完成", description: "已经通过独立验证"},
];

function storyStatusLabel(value) {
  const labels = {
    candidate: "候选",
    ready: "待开始",
    in_progress: "进行中",
    waiting: "等待",
    done: "已完成",
    cancelled: "已归档",
  };
  return labels[value] || value || "未知";
}

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

function formatTime(value) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const timezone = state.status?.activation?.timezone || "Asia/Shanghai";
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: timezone,
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  } catch (_error) {
    return date.toLocaleString("zh-CN");
  }
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

function replaceDefinitions(target, rows) {
  target.replaceChildren(...rows.map(([term, description]) => definition(term, description)));
}

function renderMarkdown(target, source, emptyText = "暂无内容。") {
  target.replaceChildren();
  const text = String(source || "").trim();
  if (!text) {
    const empty = document.createElement("p");
    empty.className = "document-empty";
    empty.textContent = emptyText;
    target.appendChild(empty);
    return;
  }

  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const isBlockStart = line => (
    /^#{1,4}\s+/.test(line)
    || /^```/.test(line)
    || /^\s*[-*]\s+/.test(line)
    || /^\s*\d+\.\s+/.test(line)
    || /^\s*>\s?/.test(line)
    || /^\s*\|/.test(line)
    || /^\s*---+\s*$/.test(line)
  );

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^```\s*(.*)$/);
    if (fence) {
      index += 1;
      const codeLines = [];
      while (index < lines.length && !/^```/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      index += 1;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codeLines.join("\n");
      if (fence[1]) {
        code.dataset.language = fence[1];
      }
      pre.appendChild(code);
      target.appendChild(pre);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(6, heading[1].length + 2);
      const element = document.createElement(`h${level}`);
      element.textContent = heading[2];
      target.appendChild(element);
      index += 1;
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    if (unordered) {
      const list = document.createElement("ul");
      while (index < lines.length) {
        const match = lines[index].match(/^\s*[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        const item = document.createElement("li");
        item.textContent = match[1];
        list.appendChild(item);
        index += 1;
      }
      target.appendChild(list);
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (ordered) {
      const list = document.createElement("ol");
      while (index < lines.length) {
        const match = lines[index].match(/^\s*\d+\.\s+(.+)$/);
        if (!match) {
          break;
        }
        const item = document.createElement("li");
        item.textContent = match[1];
        list.appendChild(item);
        index += 1;
      }
      target.appendChild(list);
      continue;
    }

    if (/^\s*\|/.test(line)) {
      const tableLines = [];
      while (index < lines.length && /^\s*\|/.test(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      const pre = document.createElement("pre");
      pre.className = "markdown-table";
      pre.textContent = tableLines.join("\n");
      target.appendChild(pre);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote = document.createElement("blockquote");
      const quoteLines = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      quote.textContent = quoteLines.join(" ");
      target.appendChild(quote);
      continue;
    }

    if (/^\s*---+\s*$/.test(line)) {
      target.appendChild(document.createElement("hr"));
      index += 1;
      continue;
    }

    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    const paragraph = document.createElement("p");
    paragraph.textContent = paragraphLines.join(" ");
    target.appendChild(paragraph);
  }
}

function extractSection(markdown, heading) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const start = lines.findIndex(line => line.trim() === `## ${heading}`);
  if (start < 0) {
    return "";
  }
  const result = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^#{1,2}\s+/.test(lines[index])) {
      break;
    }
    result.push(lines[index]);
  }
  return result.join("\n").trim();
}

function withoutTopHeading(markdown) {
  return String(markdown || "").replace(/^\s*#\s+[^\n]+\n?/, "").trim();
}

function hasPendingContent(content) {
  return content
    .replace(/暂无[。.]?/g, "")
    .replace(/[-*#`\s]/g, "")
    .trim().length > 0;
}

function renderService() {
  const runner = state.status.runner;
  const service = runner.service || {};
  const alive = Boolean(service.alive);
  document.getElementById("service-dot").className = `status-dot ${alive ? "online" : "offline"}`;
  document.getElementById("service-status").textContent = alive ? "Runner 运行中" : "Runner 已停止";

  const root = runner.active_root;
  const reporter = runner.active_reporter;
  replaceDefinitions(document.getElementById("service-details"), [
    ["Root", root ? "活跃" : "空闲"],
    ["Reporter", reporter ? "活跃" : "空闲"],
    ["下次检查", formatTime(runner.next_activation_check_at)],
  ]);
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
    const displayStatus = project.paused ? "paused" : project.status;
    meta.textContent = statusLabel(displayStatus);
    meta.className = `project-state state-${displayStatus}`;
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

function renderPendingCard({cardId, stateId, contentId, formId, source, heading, emptyText}) {
  const content = extractSection(source, heading);
  const pending = hasPendingContent(content);
  const card = document.getElementById(cardId);
  const stateBadge = document.getElementById(stateId);
  const form = document.getElementById(formId);
  card.classList.toggle("needs-attention", pending);
  stateBadge.textContent = pending ? "待处理" : "无待办";
  stateBadge.className = `pending-state ${pending ? "pending" : "clear"}`;
  form.classList.toggle("hidden", !pending);
  renderMarkdown(
    document.getElementById(contentId),
    pending ? content : "",
    emptyText,
  );
  return pending;
}

function renderAttention() {
  const files = state.project.files;
  const questionPending = renderPendingCard({
    cardId: "question-card",
    stateId: "question-state",
    contentId: "question-content",
    formId: "question-response-form",
    source: files["questions.md"],
    heading: "待人类回答",
    emptyText: "当前没有需要你决定的业务问题。",
  });
  const escalationPending = renderPendingCard({
    cardId: "escalation-card",
    stateId: "escalation-state",
    contentId: "escalation-content",
    formId: "escalation-response-form",
    source: files["escalations.md"],
    heading: "待处理",
    emptyText: "当前没有需要你介入的管控异常。",
  });
  const count = Number(questionPending) + Number(escalationPending);
  const badge = document.getElementById("attention-count");
  badge.textContent = `${count} 项`;
  badge.classList.toggle("has-items", count > 0);
}

function renderStoryBoard() {
  const board = document.getElementById("story-board");
  board.replaceChildren();
  const stories = Array.isArray(state.project.stories) ? state.project.stories : [];
  const runtime = state.project.runtime || {};

  for (const columnDefinition of storyColumns) {
    const column = document.createElement("section");
    column.className = `story-column story-column-${columnDefinition.status}`;

    const heading = document.createElement("div");
    heading.className = "story-column-heading";
    const headingText = document.createElement("div");
    const title = document.createElement("h4");
    title.textContent = columnDefinition.label;
    const description = document.createElement("p");
    description.textContent = columnDefinition.description;
    headingText.append(title, description);
    const columnStories = stories.filter(story => story.status === columnDefinition.status);
    const count = document.createElement("span");
    count.className = "story-count";
    count.textContent = String(columnStories.length);
    heading.append(headingText, count);
    column.appendChild(heading);

    const cards = document.createElement("div");
    cards.className = "story-cards";
    for (const story of columnStories) {
      const card = document.createElement("button");
      card.className = "story-card";
      card.type = "button";
      card.dataset.storyId = story.id;
      if (runtime.current_story === story.id) {
        card.classList.add("active");
      }

      const cardTop = document.createElement("div");
      cardTop.className = "story-card-top";
      const priority = document.createElement("span");
      priority.className = `story-priority priority-${String(story.priority).toLowerCase()}`;
      priority.textContent = story.priority;
      const storyId = document.createElement("code");
      storyId.textContent = story.id;
      cardTop.append(priority, storyId);

      const cardTitle = document.createElement("strong");
      cardTitle.textContent = story.title;
      const summary = document.createElement("p");
      summary.textContent = story.summary;

      const labels = document.createElement("div");
      labels.className = "story-labels";
      for (const label of (story.labels || []).slice(0, 4)) {
        const chip = document.createElement("span");
        chip.textContent = label;
        labels.appendChild(chip);
      }

      const foot = document.createElement("div");
      foot.className = "story-card-foot";
      const updated = document.createElement("span");
      updated.textContent = formatTime(story.updated_at);
      foot.appendChild(updated);
      if (runtime.current_story === story.id && runtime.story_phase) {
        const phase = document.createElement("span");
        phase.className = "story-phase";
        phase.textContent = runtime.story_phase;
        foot.appendChild(phase);
      } else if (story.waiting_on) {
        const waiting = document.createElement("span");
        waiting.className = "story-phase waiting";
        waiting.textContent = `等待 ${story.waiting_on}`;
        foot.appendChild(waiting);
      }

      card.append(cardTop, cardTitle, summary, labels, foot);
      card.addEventListener("click", () => openStory(story.id));
      cards.appendChild(card);
    }

    if (!columnStories.length) {
      const empty = document.createElement("p");
      empty.className = "story-column-empty";
      empty.textContent = "暂无";
      cards.appendChild(empty);
    }
    column.appendChild(cards);
    board.appendChild(column);
  }

  const archived = stories.filter(story => story.status === "cancelled").length;
  document.getElementById("archived-story-count").textContent = archived
    ? `${archived} 个已归档 Story`
    : "暂无归档 Story";
}

async function openStory(storyId) {
  if (!state.selectedProjectId) {
    return;
  }
  try {
    const story = await request(
      `/api/projects/${encodeURIComponent(state.selectedProjectId)}/stories/${encodeURIComponent(storyId)}`,
    );
    state.selectedStory = story;
    const metadata = story.metadata;
    document.getElementById("story-modal-id").textContent = metadata.id;
    document.getElementById("story-modal-title").textContent = metadata.title;
    document.getElementById("story-modal-summary").textContent = metadata.summary;
    document.getElementById("story-status-select").value = metadata.status;
    document.getElementById("story-priority-select").value = metadata.priority;
    document.getElementById("story-labels-input").value = (metadata.labels || []).join(", ");
    document.getElementById("story-modal-updated").textContent = formatTime(metadata.updated_at);
    renderMarkdown(document.getElementById("story-modal-body"), story.body, "Story 正文为空。");
    document.getElementById("story-modal").classList.remove("hidden");
  } catch (error) {
    showToast(error.message, true);
  }
}

function closeStoryModal() {
  state.selectedStory = null;
  document.getElementById("story-modal").classList.add("hidden");
}

async function saveStoryMetadata() {
  if (!state.selectedStory || !state.selectedProjectId) {
    return;
  }
  const storyId = state.selectedStory.metadata.id;
  const labels = document.getElementById("story-labels-input").value
    .split(",")
    .map(value => value.trim())
    .filter(Boolean);
  try {
    await request(
      `/api/projects/${encodeURIComponent(state.selectedProjectId)}/stories/${encodeURIComponent(storyId)}`,
      {
        method: "POST",
        body: JSON.stringify({
          status: document.getElementById("story-status-select").value,
          priority: document.getElementById("story-priority-select").value,
          labels,
        }),
      },
    );
    closeStoryModal();
    await loadStatus();
    showToast("Story 元数据已更新");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderDocumentBrowser() {
  const tabs = document.getElementById("document-tabs");
  tabs.replaceChildren();
  for (const [name, metadata] of Object.entries(documents)) {
    const button = document.createElement("button");
    button.textContent = metadata.label;
    button.dataset.file = name;
    if (name === state.selectedFile) {
      button.classList.add("selected");
    }
    button.addEventListener("click", () => {
      state.selectedFile = name;
      renderDocumentBrowser();
    });
    tabs.appendChild(button);
  }

  const metadata = documents[state.selectedFile];
  const meta = document.getElementById("document-meta");
  meta.replaceChildren();
  const surface = document.createElement("span");
  surface.className = `surface-tag ${metadata.surface === "业务面" ? "business" : "control"}`;
  surface.textContent = metadata.surface;
  const access = document.createElement("span");
  access.className = "access-tag readonly";
  access.textContent = metadata.access;
  const path = document.createElement("code");
  path.textContent = state.selectedFile;
  meta.append(surface, access, path);
  renderMarkdown(
    document.getElementById("document-content"),
    state.project.files[state.selectedFile],
  );
}

function renderProject() {
  if (!state.project) {
    return;
  }
  const summary = state.project.summary;
  const runtime = state.project.runtime || {};
  const runner = state.status.runner || {};
  const service = runner.service || {};
  const project = state.project.project || {};
  const displayStatus = summary.paused ? "paused" : summary.status;

  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("project-view").classList.remove("hidden");
  document.getElementById("project-controls").classList.remove("hidden");
  document.getElementById("project-name").textContent = summary.name;
  document.getElementById("project-path").textContent = summary.path;

  const stateChip = document.getElementById("project-state-chip");
  stateChip.textContent = statusLabel(displayStatus);
  stateChip.className = `state-chip state-${displayStatus}`;

  const pauseButton = document.getElementById("pause-button");
  pauseButton.textContent = summary.paused ? "恢复项目" : "暂停项目";
  pauseButton.dataset.action = summary.paused ? "resume" : "pause";

  const currentStory = (state.project.stories || []).find(
    story => story.id === summary.current_story,
  );
  document.getElementById("current-story").textContent = currentStory
    ? currentStory.title
    : "暂无正在执行的 Story";
  document.getElementById("last-result").textContent = summary.last_result || "尚未产生工作结果。";
  document.getElementById("last-activity").textContent = formatTime(summary.last_activity_at);
  document.getElementById("project-status").textContent = statusLabel(displayStatus);
  document.getElementById("runtime-summary").textContent = summary.paused
    ? "项目已暂停，不会开始新的 Story。"
    : `${runtime.active_sessions?.length || 0} 个已登记活动会话`;
  document.getElementById("window-summary").textContent = (summary.windows || []).join("，") || "未配置";

  const windowInput = document.getElementById("window-text");
  if (document.activeElement !== windowInput) {
    windowInput.value = (summary.windows || []).join(", ");
  }

  renderAttention();
  renderStoryBoard();
  renderMarkdown(
    document.getElementById("latest-report"),
    withoutTopHeading(state.project.files["reports/latest.md"]),
    "尚未生成日报。",
  );
  replaceDefinitions(document.getElementById("health-details"), [
    ["Runner", service.alive ? "运行中" : "已停止"],
    ["Root Supervisor", runner.active_root ? "活跃" : "空闲"],
    ["Reporter", runner.active_reporter ? "活跃" : "空闲"],
    ["上次巡检", formatTime(runner.last_activation_check_at)],
    ["下次巡检", formatTime(runner.next_activation_check_at)],
  ]);

  const sessions = Array.isArray(runtime.active_sessions) ? runtime.active_sessions : [];
  const sessionSummary = sessions.length
    ? sessions.map(session => session.session || session.name || String(session)).join("，")
    : "无";
  replaceDefinitions(document.getElementById("agent-details"), [
    ["Agent", project.agent?.kind || "未配置"],
    ["启动方式", "Runner 统一管理"],
    ["已登记会话", sessionSummary],
    ["项目状态", statusLabel(displayStatus)],
    ["当前 Story", currentStory ? currentStory.id : "无"],
    ["Story 阶段", runtime.story_phase || "无"],
    ["最近活动", formatTime(summary.last_activity_at)],
  ]);

  renderDocumentBrowser();
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
    showToast("业务指令已写入 Inbox");
  } catch (error) {
    showToast(error.message, true);
  }
});

for (const button of document.querySelectorAll(".response-submit")) {
  button.addEventListener("click", async () => {
    const input = document.getElementById(button.dataset.input);
    try {
      await postProject("response", {channel: button.dataset.channel, text: input.value});
      input.value = "";
      showToast("回复已追加，Agent 下次激活时会读取");
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

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

document.getElementById("jump-to-schedule").addEventListener("click", () => {
  document.getElementById("control-center").scrollIntoView({behavior: "smooth", block: "start"});
  window.setTimeout(() => document.getElementById("window-text").focus(), 420);
});

document.getElementById("story-modal-close").addEventListener("click", closeStoryModal);
document.getElementById("story-modal-cancel").addEventListener("click", closeStoryModal);
document.getElementById("story-modal-save").addEventListener("click", saveStoryMetadata);
document.getElementById("story-modal").addEventListener("click", event => {
  if (event.target.id === "story-modal") {
    closeStoryModal();
  }
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    closeStoryModal();
  }
});

loadStatus(false);
window.setInterval(() => loadStatus(), 15000);
