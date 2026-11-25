(function () {
  "use strict";
  const root = document.getElementById("survey-health");
  if (!root) return;
  const models = JSON.parse(document.getElementById("survey-health-models").textContent);
  const $ = (id) => document.getElementById(id);
  const runButton = $("survey-health-run");
  const stopButton = $("survey-health-stop");
  const status = $("survey-health-status");
  const progress = $("survey-health-progress");
  const progressTrack = $("survey-health-progress-track");
  const progressBar = progress.querySelector("span");
  const progressLabel = $("survey-health-progress-label");
  const checked = $("survey-health-checked");
  const failing = $("survey-health-failing");
  const issueCount = $("survey-health-issues");
  const scanErrorCount = $("survey-health-scan-errors");
  const incomplete = $("survey-health-incomplete");
  const list = $("survey-health-list");
  const empty = $("survey-health-empty");
  const resultsCount = $("survey-health-results-count");
  const errorSection = $("survey-health-scan-errors-section");
  const errorList = $("survey-health-scan-errors-list");
  const modelFilter = $("survey-health-filter-model");
  const fieldFilter = $("survey-health-filter-field");
  const codeFilter = $("survey-health-filter-code");
  const textFilter = $("survey-health-filter-text");
  const pagination = $("survey-health-pagination");
  const previous = $("survey-health-prev");
  const next = $("survey-health-next");
  const pageLabel = $("survey-health-page-label");
  const pageSize = 50;
  const maxFindings = 5000;
  const maxScanErrors = 1000;
  const emptyStateText = {
    completed: "No validation findings were found.",
    incomplete: "No validation findings were completed before the run stopped. Review the scan errors below.",
    running: "No findings have been reported yet. The health check is still running.",
    never: "Run the check to see findings here.",
  };
  let controller = null;
  let running = false;
  let stopRequested = false;
  let findings = [];
  let scanErrors = [];
  let page = 1;
  let runState = "never";
  let summary = { checked: 0, failing: 0, issues: 0 };
  let totalObjects = null;
  let determinateProgress = false;
  let progressPercent = 0;

  function csrfToken() {
    const token = document.querySelector("#survey-health-csrf-form input[name=csrfmiddlewaretoken]");
    return token ? token.value : "";
  }
  function modelLabel(key) {
    const model = models.find((item) => item.key === key);
    return model ? model.label : key || "Unknown model";
  }
  function setStatus(message) { status.textContent = message; }
  function setProgressMetadata(text, value, visibleText = text) {
    if (value == null) {
      ["aria-valuemin", "aria-valuemax", "aria-valuenow"].forEach((attribute) => progressTrack.removeAttribute(attribute));
    } else {
      progressTrack.setAttribute("aria-valuemin", "0");
      progressTrack.setAttribute("aria-valuemax", "100");
      progressTrack.setAttribute("aria-valuenow", value);
    }
    progressTrack.setAttribute("aria-valuetext", text);
    progressLabel.textContent = visibleText;
  }
  function setIndeterminateProgress(label) {
    determinateProgress = false;
    progressTrack.classList.add("is-indeterminate");
    progressBar.style.width = "";
    const visibleText = `${label} · ${summary.checked} objects checked`;
    setProgressMetadata(`${visibleText}; total unavailable`, null, visibleText);
  }
  function setDeterminateProgress(label, complete) {
    determinateProgress = true;
    progressTrack.classList.remove("is-indeterminate");
    const total = totalObjects || 0;
    const rawPercent = total ? (summary.checked / total) * 100 : 0;
    const candidate = complete ? 100 : Math.min(99.99, Math.max(0, rawPercent));
    progressPercent = Math.max(progressPercent, Number(candidate.toFixed(2)));
    progressBar.style.width = `${progressPercent.toFixed(2)}%`;
    let totalText;
    if (complete) {
      totalText = summary.checked > total
        ? `${summary.checked} objects checked (initial total ${total})`
        : `${summary.checked} objects checked`;
    } else if (summary.checked > total) {
      totalText = `${summary.checked} objects checked (initial total ${total})`;
    } else {
      totalText = `${summary.checked} / ${total} objects checked`;
    }
    const displayedPercent = complete ? 100 : Math.min(99, Math.round(progressPercent));
    const text = `${label} · ${totalText} (${displayedPercent}%)`;
    setProgressMetadata(text, progressPercent.toFixed(2));
  }
  function updateProgress(label) {
    if (determinateProgress) setDeterminateProgress(label, false);
    else setIndeterminateProgress(label);
  }
  function finishWithoutTotal(label, width) {
    progressTrack.classList.remove("is-indeterminate");
    progressBar.style.width = width;
    const visibleText = `${label} · ${summary.checked} objects checked`;
    setProgressMetadata(`${visibleText}; total unavailable`, null, visibleText);
  }
  function finishProgress(completed) {
    if (completed) {
      if (determinateProgress) {
        setDeterminateProgress("Complete", true);
      } else {
        progressPercent = 100;
        finishWithoutTotal("Complete", "100%");
      }
      return;
    }
    if (determinateProgress) setDeterminateProgress("Incomplete", false);
    else {
      finishWithoutTotal("Incomplete", `${progressPercent}%`);
    }
  }
  function addText(parent, tag, value, className) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value == null ? "" : String(value);
    parent.appendChild(element);
    return element;
  }
  function editLink(item) {
    if (!item.edit_url) return null;
    const link = document.createElement("a");
    link.href = item.edit_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Edit object (opens in a new tab)";
    link.setAttribute("aria-label", `Edit ${item.name || "object"} in a new tab`);
    return link;
  }
  function renderSummary() {
    checked.textContent = String(summary.checked);
    failing.textContent = String(summary.failing);
    issueCount.textContent = String(summary.issues);
    scanErrorCount.textContent = String(scanErrors.length);
  }
  function renderAll() {
    renderSummary();
    renderScanErrors();
    renderResults();
  }
  function matches(item) {
    const code = codeFilter.value.trim().toLowerCase();
    const search = textFilter.value.trim().toLowerCase();
    if (modelFilter.value && item.model !== modelFilter.value) return false;
    if (fieldFilter.value && item.field !== fieldFilter.value) return false;
    if (code && !String(item.code || "").toLowerCase().includes(code)) return false;
    if (search && ![item.name, item.message, item.suggestion, item.expression]
      .map((value) => String(value || "").toLowerCase()).join(" ").includes(search)) return false;
    return true;
  }
  function renderFinding(item) {
    const article = document.createElement("article");
    article.className = "survey-health-finding";
    article.setAttribute("aria-label", `${item.code || "Scan issue"} on ${item.name || "object"}`);
    const heading = document.createElement("div");
    heading.className = "survey-health-finding-heading";
    const identity = document.createElement("div");
    addText(identity, "h3", item.name || "Unnamed object");
    addText(identity, "p", `${item.model_label || modelLabel(item.model)} · ID ${item.id} · ${item.is_active ? "Active" : "Inactive"}`, "survey-health-object-meta");
    heading.appendChild(identity);
    const code = addText(heading, "span", item.code || "Unknown issue", "survey-health-code");
    code.title = item.code || "";
    article.appendChild(heading);
    const details = document.createElement("dl");
    details.className = "survey-health-finding-details";
    addText(details, "dt", "Field");
    addText(details, "dd", item.field_label || item.field || "General");
    addText(details, "dt", "Why");
    addText(details, "dd", item.message || "The object could not be validated.");
    addText(details, "dt", "Suggested action");
    addText(details, "dd", item.suggestion || "Review the expression and save it again.");
    if (item.expression) {
      addText(details, "dt", "Expression");
      addText(details, "dd", item.expression, "survey-health-expression").setAttribute("dir", "auto");
    }
    article.appendChild(details);
    const link = editLink(item);
    if (link) {
      const actions = document.createElement("div");
      actions.className = "survey-health-finding-actions";
      actions.appendChild(link);
      article.appendChild(actions);
    }
    return article;
  }
  function renderResults() {
    const filtered = findings.filter(matches);
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    page = Math.min(page, totalPages);
    const start = (page - 1) * pageSize;
    list.replaceChildren();
    filtered.slice(start, start + pageSize).forEach((item) => list.appendChild(renderFinding(item)));
    empty.hidden = filtered.length !== 0;
    if (!filtered.length) empty.textContent = findings.length
      ? "No findings match these filters." : emptyStateText[runState];
    pagination.hidden = filtered.length <= pageSize;
    previous.disabled = page <= 1;
    next.disabled = page >= totalPages;
    pageLabel.textContent = `Page ${page} of ${totalPages}`;
    resultsCount.textContent = filtered.length ? `${filtered.length} finding${filtered.length === 1 ? "" : "s"}` : "No results";
  }
  function renderScanErrors() {
    errorList.replaceChildren();
    scanErrors.forEach((item) => {
      const row = document.createElement("div");
      row.className = "survey-health-scan-error";
      addText(row, "strong", `${item.name || "Batch"} · ${item.code || "Scan error"}`);
      addText(row, "p", `${item.model_label || modelLabel(item.model)}${item.id ? ` · ID ${item.id}` : ""}: ${item.message || "The object could not be checked."}`);
      addText(row, "p", `Suggested action: ${item.suggestion || "Review the object and run the health check again after making a safe correction."}`);
      const link = editLink(item);
      if (link) {
        row.appendChild(link);
      }
      errorList.appendChild(row);
    });
    errorSection.hidden = !scanErrors.length;
  }
  function appendPayload(payload) {
    summary.checked += Number(payload.checked_objects || 0);
    summary.failing += Number(payload.failing_objects || 0);
    summary.issues += Number(payload.issue_count || 0);
    findings.push(...(payload.issues || []));
    scanErrors.push(...(payload.scan_errors || []));
    if (findings.length > maxFindings || scanErrors.length > maxScanErrors) {
      findings = findings.slice(0, maxFindings);
      scanErrors = scanErrors.slice(0, maxScanErrors);
      renderAll();
      return false;
    }
    renderAll();
    return true;
  }
  async function postScan(body) {
    const response = await fetch(root.dataset.scanUrl, {
      method: "POST", credentials: "same-origin", signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.status === "error") {
      throw new Error(payload.message || "The health check could not continue.");
    }
    return payload;
  }
  async function loadTotals() {
    setIndeterminateProgress("Preparing progress totals…");
    try {
      const payload = await postScan({ action: "totals" });
      if (stopRequested) throw new DOMException("Health check stopped", "AbortError");
      if (!payload.totals) {
        throw new Error("Progress totals were unavailable.");
      }
      const counts = models.map((model) => Number(payload.totals[model.key]));
      if (counts.some((count) => !Number.isSafeInteger(count) || count < 0)) {
        throw new Error("Progress totals were invalid.");
      }
      totalObjects = counts.reduce((total, count) => total + count, 0);
      determinateProgress = true;
      updateProgress("Preparing");
    } catch (error) {
      if (stopRequested) throw new DOMException("Health check stopped", "AbortError");
      totalObjects = null;
      setIndeterminateProgress("Checking survey data");
      setStatus("Health check running; the total count is unavailable.");
    }
  }
  function resetRun() {
    findings = [];
    scanErrors = [];
    summary = { checked: 0, failing: 0, issues: 0 };
    totalObjects = null;
    determinateProgress = false;
    progressPercent = 0;
    page = 1;
    incomplete.hidden = true;
    errorSection.hidden = true;
    errorList.replaceChildren();
    renderSummary();
    renderResults();
    setIndeterminateProgress("Preparing progress totals…");
  }
  async function run() {
    if (running) return;
    running = true;
    runState = "running";
    stopRequested = false;
    controller = new AbortController();
    runButton.disabled = true;
    stopButton.disabled = false;
    progress.hidden = false;
    progress.setAttribute("aria-hidden", "false");
    resetRun();
    setStatus("Health check running…");
    let completed = false;
    try {
      await loadTotals();
      if (stopRequested) throw new DOMException("Health check stopped", "AbortError");
      for (let modelIndex = 0; modelIndex < models.length; modelIndex += 1) {
        const model = models[modelIndex];
        let cursor = 0;
        while (true) {
          if (stopRequested) throw new DOMException("Health check stopped", "AbortError");
          updateProgress(model.label);
          setStatus(`Checking ${model.label}…`);
          const payload = await postScan({ model: model.key, after_pk: cursor, limit: 25 });
          if (!appendPayload(payload)) throw new Error("The health check output limit was reached; the run is incomplete.");
          updateProgress(model.label);
          if (!payload.page_processed) throw new Error(payload.incomplete_reason || "The health check is incomplete.");
          if (stopRequested) {
            setStatus("Stopping after current batch…");
            throw new DOMException("Health check stopped", "AbortError");
          }
          if (!payload.has_more) break;
          if (!payload.next_cursor) throw new Error("The health check returned no next cursor.");
          cursor = payload.next_cursor;
          await new Promise((resolve) => window.setTimeout(resolve, 120));
        }
      }
      completed = true;
    } catch (error) {
      setStatus(error.name === "AbortError" && stopRequested ? "Health check stopped. Results are incomplete." : "Health check incomplete.");
      incomplete.textContent = error.name === "AbortError" && stopRequested ? "Health check stopped before all models were checked." : (error.message || "The health check stopped before all models were checked.");
      incomplete.hidden = false;
    } finally {
      runState = completed ? "completed" : "incomplete";
      if (completed && scanErrors.length) {
        completed = false;
        runState = "incomplete";
        incomplete.textContent = "The run reached the end of the data, but one or more objects were skipped and need attention.";
        incomplete.hidden = false;
        setStatus("Health check incomplete: scan errors were found.");
      }
      running = false;
      controller = null;
      runButton.disabled = false;
      runButton.textContent = "Run again";
      stopButton.disabled = true;
      finishProgress(completed);
      if (completed) setStatus(scanErrors.length ? "Health check complete with scan errors." : "Health check complete.");
      renderAll();
    }
  }
  runButton.addEventListener("click", run);
  stopButton.addEventListener("click", () => {
    if (!running) return;
    stopRequested = true;
    stopButton.disabled = true;
    setStatus("Stopping after current batch…");
  });
  [modelFilter, fieldFilter, codeFilter, textFilter].forEach((element) => {
    element.addEventListener("input", () => { page = 1; renderResults(); });
    element.addEventListener("change", () => { page = 1; renderResults(); });
  });
  previous.addEventListener("click", () => { page = Math.max(1, page - 1); renderResults(); });
  next.addEventListener("click", () => { page += 1; renderResults(); });
})();
