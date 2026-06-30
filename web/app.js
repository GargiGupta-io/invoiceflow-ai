const uploadForm = document.getElementById("upload-form");
const uploadWorkflowHint = document.getElementById("upload-workflow-hint");
const uploadGuidance = document.getElementById("upload-guidance");
const loadingCue = document.getElementById("loading-cue");
const loadingCueText = document.getElementById("loading-cue-text");
const sampleStatus = document.getElementById("sample-status");
const uploadStatus = document.getElementById("upload-status");
const resultKind = document.getElementById("result-kind");
const routeValue = document.getElementById("route-value");
const routeReason = document.getElementById("route-reason");
const documentValue = document.getElementById("document-value");
const documentText = document.getElementById("document-text");
const decisionValue = document.getElementById("decision-value");
const decisionSummary = document.getElementById("decision-summary");
const decisionExplainer = document.getElementById("decision-explainer");
const whyDecisionList = document.getElementById("why-decision-list");
const confidenceValue = document.getElementById("confidence-value");
const riskText = document.getElementById("risk-text");
const reviewValue = document.getElementById("review-value");
const reviewText = document.getElementById("review-text");
const decisionEvidenceValue = document.getElementById("decision-evidence-value");
const decisionEvidenceText = document.getElementById("decision-evidence-text");
const evidenceCount = document.getElementById("evidence-count");
const evidenceText = document.getElementById("evidence-text");
const auditValue = document.getElementById("audit-value");
const auditText = document.getElementById("audit-text");
const anomalyList = document.getElementById("anomaly-list");
const signalList = document.getElementById("signal-list");
const evidenceList = document.getElementById("evidence-list");
const agentTraceList = document.getElementById("agent-trace-list");
const keyFieldList = document.getElementById("key-field-list");
const auditDetailList = document.getElementById("audit-detail-list");
const flowExtractionStatus = document.getElementById("flow-extraction-status");
const flowExtractionDetail = document.getElementById("flow-extraction-detail");
const flowRetrievalStatus = document.getElementById("flow-retrieval-status");
const flowRetrievalDetail = document.getElementById("flow-retrieval-detail");
const flowValidationStatus = document.getElementById("flow-validation-status");
const flowValidationDetail = document.getElementById("flow-validation-detail");
const flowDecisionStatus = document.getElementById("flow-decision-status");
const flowDecisionDetail = document.getElementById("flow-decision-detail");
const guardrailPanel = document.getElementById("guardrail-panel");
const rawJson = document.getElementById("raw-json");
const sampleRunButtons = document.querySelectorAll("[data-run-sample]");
const resultsPanel = document.querySelector(".results-panel");
const entryWorkflowState = document.getElementById("entry-workflow-state");
const entryWorkflowDetail = document.getElementById("entry-workflow-detail");
const entrySampleCount = document.getElementById("entry-sample-count");
const entryAuditState = document.getElementById("entry-audit-state");
const entryAuditDetail = document.getElementById("entry-audit-detail");
const reviewQueueStatus = document.getElementById("review-queue-status");
const reviewQueueSummary = document.getElementById("review-queue-summary");
const reviewQueueBody = document.getElementById("review-queue-body");
const reviewQueueMeta = document.getElementById("review-queue-meta");
const reviewQueueRefresh = document.getElementById("review-queue-refresh");
const evalDashboardStatus = document.getElementById("eval-dashboard-status");
const evalDashboardSummary = document.getElementById("eval-dashboard-summary");
const evalDashboardMeta = document.getElementById("eval-dashboard-meta");
const evalDashboardRefresh = document.getElementById("eval-dashboard-refresh");
const evalResultsLink = document.getElementById("eval-results-link");
const evalFailureBody = document.getElementById("eval-failure-body");
const evalDatasetSize = document.getElementById("eval-dataset-size");
const evalPassedCases = document.getElementById("eval-passed-cases");
const evalPassRate = document.getElementById("eval-pass-rate");
const evalRoutingRate = document.getElementById("eval-routing-rate");
const evalExtractionRate = document.getElementById("eval-extraction-rate");
const evalCitationRate = document.getElementById("eval-citation-rate");
const evalGroundingRate = document.getElementById("eval-grounding-rate");
const evalReviewRate = document.getElementById("eval-review-rate");
const evalSubjectRate = document.getElementById("eval-subject-rate");
const evalMentionRate = document.getElementById("eval-mention-rate");
const evalLatency = document.getElementById("eval-latency");
const evalGeneratedAt = document.getElementById("eval-generated-at");
const tabButtons = document.querySelectorAll("[data-tab-target]");
const tabPanels = document.querySelectorAll("[data-tab-panel]");
const visibleDemoCases = {
  ap_001_clean_invoice: "Clean Invoice",
  ap_002_missing_po: "Missing PO Invoice",
  ap_004_duplicate_invoice: "Duplicate Invoice Risk",
  ap_003_threshold_review: "High-Value Approval Required",
  ar_003_payment_claim_no_proof: "AR Overdue Follow-Up"
};
let loadingCueTimer = null;
let activeSampleId = null;

activateTab("workflow");
bootstrap();
reviewQueueRefresh.addEventListener("click", () => {
  loadReviewQueue();
});
evalDashboardRefresh.addEventListener("click", () => {
  loadEvalDashboard(true);
});

for (const button of sampleRunButtons) {
  button.dataset.defaultLabel = button.textContent;
  button.addEventListener("click", () => {
    const sampleId = button.dataset.runSample;
    if (sampleId) {
      runSampleWorkflow(sampleId, "auto", button);
    }
  });
}

for (const button of tabButtons) {
  button.addEventListener("click", () => {
    const target = button.dataset.tabTarget;
    if (target) {
      activateTab(target);
    }
  });
}

async function bootstrap() {
  setStatus(sampleStatus, "Loading samples", "running");
  try {
    const response = await fetch("/samples");
    const payload = await response.json();
    const samples = payload.samples || [];
    updateEntrySampleCount(samples);
    await loadReviewQueue();
    await loadEvalDashboard();
    setStatus(sampleStatus, "Ready", "success");
  } catch (error) {
    setStatus(sampleStatus, "Failed to load samples", "error");
    rawJson.textContent = formatError(error);
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("upload-file");
  const extractorMode = "auto";
  const workflowHint = uploadWorkflowHint.value;

  if (!fileInput.files || fileInput.files.length === 0) {
    setStatus(uploadStatus, "Choose a file first", "error");
    setUploadGuidance("Choose a PDF, .txt, or .md file, or run a sample case instead.", true);
    entryWorkflowState.textContent = "No file selected";
    entryWorkflowDetail.textContent = "Upload a supported finance document or start with one of the sample cases.";
    return;
  }

  const selectedFile = fileInput.files[0];
  if (!isSupportedUploadFile(selectedFile)) {
    setStatus(uploadStatus, "Unsupported file", "error");
    setUploadGuidance("Unsupported file type. Use a text-based PDF, .txt, or .md file. If the source is an image or scan, paste text into a .txt file first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("extractor_mode", extractorMode);
  formData.append("workflow_hint", workflowHint);

  setStatus(uploadStatus, "Uploading", "running");
  setUploadGuidance("Uploading and parsing the document. If OCR is needed, use the text fallback because OCR is not configured in this preview.", false);
  showLoadingCue(buildLoadingStages(`Uploading ${workflowHint.toUpperCase()} file`));
  try {
    const response = await fetch("/workflow/upload", {
      method: "POST",
      body: formData
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(payload.detail, "Upload workflow failed."));
    }
    renderResult(payload);
    setActiveSample(null);
    setStatus(uploadStatus, "Completed", "success");
    setUploadGuidance("Upload complete. Review the recommendation, evidence, and human review status below.", false);
    setWorkspaceReady();
    loadReviewQueue();
  } catch (error) {
    const friendlyError = buildUploadErrorMessage(error);
    setStatus(uploadStatus, "Run failed", "error");
    setUploadGuidance(friendlyError, true);
    entryWorkflowState.textContent = "Upload needs attention";
    entryWorkflowDetail.textContent = friendlyError;
    entryAuditState.textContent = "No result generated";
    entryAuditDetail.textContent = "Try a text-based PDF, .txt file, .md file, or one of the sample cases.";
    rawJson.textContent = friendlyError;
    setWorkspaceReady();
  } finally {
    hideLoadingCue();
  }
});

function updateEntrySampleCount(samples) {
  const visibleIds = new Set(Object.keys(visibleDemoCases));
  const availableVisibleCases = samples.filter((sample) => visibleIds.has(sample.sample_id));
  const apCount = availableVisibleCases.filter((sample) => sample.category === "invoices").length;
  const arCount = availableVisibleCases.filter((sample) => sample.category === "emails").length;
  entrySampleCount.textContent = `${availableVisibleCases.length} curated cases`;
  const arLabel = arCount === 1 ? "case is" : "cases are";
  entryWorkflowDetail.textContent = `${apCount} AP review cases and ${arCount} AR follow-up ${arLabel} ready for the guided demo.`;
}

function activateTab(targetTab) {
  for (const button of tabButtons) {
    const isActive = button.dataset.tabTarget === targetTab;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  }

  for (const panel of tabPanels) {
    panel.hidden = panel.dataset.tabPanel !== targetTab;
  }
}

function setWorkspaceReady() {
  document.body.classList.add("workspace-ready");
  activateTab("workflow");
}

function buildLoadingStages(firstStage) {
  return [
    firstStage,
    "Extracting key facts",
    "Retrieving policy evidence",
    "Checking risk signals",
    "Preparing recommendation"
  ];
}

function showLoadingCue(stages) {
  if (!loadingCue) {
    return;
  }
  const stageList = Array.isArray(stages) ? stages : [stages].filter(Boolean);
  if (loadingCueTimer) {
    clearInterval(loadingCueTimer);
    loadingCueTimer = null;
  }
  if (loadingCueText && stageList.length) {
    let stageIndex = 0;
    loadingCueText.textContent = stageList[stageIndex];
    loadingCueTimer = setInterval(() => {
      stageIndex = Math.min(stageIndex + 1, stageList.length - 1);
      loadingCueText.textContent = stageList[stageIndex];
      if (stageIndex === stageList.length - 1 && loadingCueTimer) {
        clearInterval(loadingCueTimer);
        loadingCueTimer = null;
      }
    }, 850);
  }
  document.body.classList.add("workflow-running");
  loadingCue.hidden = false;
}

function hideLoadingCue() {
  if (loadingCueTimer) {
    clearInterval(loadingCueTimer);
    loadingCueTimer = null;
  }
  if (loadingCue) {
    loadingCue.hidden = true;
  }
  document.body.classList.remove("workflow-running");
}

function isSupportedUploadFile(file) {
  if (!file || !file.name) {
    return false;
  }
  return /\.(pdf|txt|md)$/i.test(file.name);
}

function setUploadGuidance(message, isError = false) {
  if (!uploadGuidance) {
    return;
  }
  uploadGuidance.textContent = message;
  uploadGuidance.classList.toggle("is-error", isError);
}

function buildUploadErrorMessage(error) {
  const message = formatError(error);
  const normalized = message.toLowerCase();

  if (normalized.includes("empty")) {
    return "The uploaded file appears to be empty. Try another file or run a sample case.";
  }
  if (normalized.includes("unsupported")) {
    return "This file type is not supported here. Use a text-based PDF, .txt, or .md file.";
  }
  if (normalized.includes("ocr") || normalized.includes("extractable text") || normalized.includes("pdf_text_extraction_empty")) {
    return "OCR is not configured in this environment. Text-based PDFs and pasted text files still work.";
  }
  if (normalized.includes("parse") || normalized.includes("extraction") || normalized.includes("schema")) {
    return "The document could not be parsed into the expected finance fields. Try a cleaner text-based file or run a sample case.";
  }
  return `${message} Try a text-based PDF, .txt, .md, or one of the sample cases.`;
}

async function loadReviewQueue() {
  setStatus(reviewQueueStatus, "Loading", "running");
  try {
    const response = await fetch("/review-queue");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(payload.detail, "Review queue failed."));
    }
    renderReviewQueue(payload);
    setStatus(reviewQueueStatus, "Ready", "success");
  } catch (error) {
    setStatus(reviewQueueStatus, "Queue error", "error");
    renderReviewQueueError(error);
  }
}

async function loadEvalDashboard(refresh = false) {
  setStatus(evalDashboardStatus, "Loading", "running");
  try {
    const response = await fetch(`/eval/summary${refresh ? "?refresh=1" : ""}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(payload.detail, "Evaluation dashboard failed."));
    }
    renderEvalDashboard(payload);
    setStatus(evalDashboardStatus, payload.failing_case_count ? "Needs review" : "Ready", payload.failing_case_count ? "warning" : "success");
  } catch (error) {
    setStatus(evalDashboardStatus, "Eval error", "error");
    renderEvalDashboardError(error);
  }
}

function renderReviewQueue(payload) {
  const items = Array.isArray(payload.items) ? payload.items : [];
  reviewQueueBody.innerHTML = "";

  if (!items.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "queue-empty";
    cell.textContent = "No review items are waiting.";
    row.appendChild(cell);
    reviewQueueBody.appendChild(row);
  } else {
    for (const item of items) {
      reviewQueueBody.appendChild(buildQueueRow(item));
    }
  }

  reviewQueueSummary.textContent = `${items.length} cases are shown from the bundled AP and AR samples.`;
  reviewQueueMeta.textContent = `Generated ${formatQueueTimestamp(payload.generated_at_utc)} | extractor mode ${payload.extractor_mode || "heuristic"}`;
}

function renderReviewQueueError(error) {
  reviewQueueBody.innerHTML = "";
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 7;
  cell.className = "queue-empty";
  cell.textContent = formatError(error);
  row.appendChild(cell);
  reviewQueueBody.appendChild(row);
  reviewQueueSummary.textContent = "The queue could not be loaded.";
  reviewQueueMeta.textContent = formatError(error);
}

function renderEvalDashboard(payload) {
  const summary = payload.summary || {};
  const totalCases = Number(summary.total_cases || 0);
  const passedCases = Number(summary.passed_cases || 0);
  const failingCases = Array.isArray(payload.failing_cases) ? payload.failing_cases : [];
  const passRate = formatPercent(summary.pass_rate);

  evalResultsLink.href = payload.download_url || "/eval-results.json";
  evalDashboardSummary.textContent = `${payload.dataset_name || "invoiceflow-ai-v1"} shows ${passedCases}/${totalCases} cases passing with ${failingCases.length} failing cases.`;
  evalDashboardMeta.textContent = `Latest run ${formatQueueTimestamp(payload.generated_at_utc)} | extractor mode ${payload.extractor_mode || "heuristic"} | ${payload.results_url || "/eval-results.json"}`;

  setEvalMetric(evalDatasetSize, String(totalCases), `${payload.dataset_name || "invoiceflow-ai-v1"} bundled cases`);
  setEvalMetric(evalPassedCases, String(passedCases), "Cases that passed every check");
  setEvalMetric(evalPassRate, passRate, "Overall evaluation success rate");
  setEvalMetric(evalRoutingRate, formatPercent(summary.workflow_match_rate), "AP and AR routing accuracy");
  setEvalMetric(evalExtractionRate, formatPercent(summary.extraction_field_match_rate), "Field match accuracy");
  setEvalMetric(evalCitationRate, formatPercent(summary.citation_check_pass_rate), "Citation coverage accuracy");
  setEvalMetric(evalGroundingRate, formatPercent(summary.grounding_support_pass_rate), "Evidence grounding accuracy");
  setEvalMetric(evalReviewRate, formatPercent(summary.human_review_rate), "How often review was required");
  setEvalMetric(evalSubjectRate, formatPercent(summary.subject_check_pass_rate), "AR subject check accuracy");
  setEvalMetric(evalMentionRate, formatPercent(summary.mention_check_pass_rate), "AR draft check accuracy");
  setEvalMetric(evalLatency, formatDuration(summary.average_latency_ms), "Average runtime per case");
  setEvalMetric(evalGeneratedAt, formatQueueTimestamp(payload.generated_at_utc), "Latest eval snapshot");

  renderEvalFailures(failingCases);
}

function renderEvalDashboardError(error) {
  evalDashboardSummary.textContent = "The evaluation dashboard could not be loaded.";
  evalDashboardMeta.textContent = formatError(error);
  evalResultsLink.href = "/eval-results.json";
  evalFailureBody.innerHTML = "";
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 4;
  cell.className = "queue-empty";
  cell.textContent = formatError(error);
  row.appendChild(cell);
  evalFailureBody.appendChild(row);
  clearEvalMetric(evalDatasetSize);
  clearEvalMetric(evalPassedCases);
  clearEvalMetric(evalPassRate);
  clearEvalMetric(evalRoutingRate);
  clearEvalMetric(evalExtractionRate);
  clearEvalMetric(evalCitationRate);
  clearEvalMetric(evalGroundingRate);
  clearEvalMetric(evalReviewRate);
  clearEvalMetric(evalSubjectRate);
  clearEvalMetric(evalMentionRate);
  clearEvalMetric(evalLatency);
  clearEvalMetric(evalGeneratedAt);
}

function renderEvalFailures(failingCases) {
  evalFailureBody.innerHTML = "";

  if (!failingCases.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "queue-empty";
    cell.textContent = "All bundled eval cases passed.";
    row.appendChild(cell);
    evalFailureBody.appendChild(row);
    return;
  }

  for (const item of failingCases) {
    const row = document.createElement("tr");
    row.appendChild(buildQueueCell(item.sample_id, "queue-case"));
    row.appendChild(buildQueueCell(prettifyWorkflow(item.workflow_type), "queue-workflow"));
    row.appendChild(buildQueueCell(formatDuration(item.latency_ms), "queue-time"));
    row.appendChild(buildQueueCell((item.failed_checks || []).join(", ") || "-", "queue-reason"));
    evalFailureBody.appendChild(row);
  }
}

function setEvalMetric(node, value, detail) {
  if (!node) {
    return;
  }
  node.textContent = value || "-";
  const card = node.closest(".eval-metric");
  if (!card) {
    return;
  }
  const text = card.querySelector("p");
  if (text && detail) {
    text.textContent = detail;
  }
}

function clearEvalMetric(node) {
  if (!node) {
    return;
  }
  node.textContent = "-";
}

function buildQueueRow(item) {
  const row = document.createElement("tr");
  row.appendChild(buildQueueCell(item.case_id, "queue-case"));
  row.appendChild(buildQueueCell(prettifyWorkflow(item.workflow_type), "queue-workflow"));
  row.appendChild(buildQueueCell(prettifyQueueValue(item.recommendation), "queue-recommendation"));
  row.appendChild(buildQueueCell(item.risk_level || "-", `queue-risk ${mapQueueRiskKind(item.risk_level)}`));
  row.appendChild(buildQueueCell(item.reason_for_review || "-", "queue-reason"));
  row.appendChild(buildQueueCell(formatQueueTimestamp(item.timestamp_utc), "queue-time"));
  row.appendChild(buildQueueStatusCell(item.status || "Needs Review", mapQueueStatusKind(item.status)));
  return row;
}

function buildQueueCell(value, className) {
  const cell = document.createElement("td");
  cell.className = className;
  cell.textContent = value || "-";
  return cell;
}

function buildQueueStatusCell(value, kind) {
  const cell = document.createElement("td");
  const pill = document.createElement("span");
  pill.className = `queue-status ${kind}`;
  pill.textContent = value || "-";
  cell.appendChild(pill);
  return cell;
}

function mapQueueRiskKind(riskLevel) {
  const value = String(riskLevel || "").toLowerCase();
  if (value.includes("high")) {
    return "error";
  }
  if (value.includes("medium")) {
    return "warning";
  }
  return "success";
}

function mapQueueStatusKind(status) {
  const value = String(status || "").toLowerCase();
  if (value === "approved") {
    return "success";
  }
  if (value === "returned for info") {
    return "warning";
  }
  if (value === "rejected" || value === "escalated") {
    return "error";
  }
  return "neutral";
}

function prettifyQueueValue(value) {
  if (!value) {
    return "-";
  }
  if (value === "approve" || value === "review" || value === "reject" || value === "missing_info") {
    return formatRecommendation(value);
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatQueueTimestamp(timestamp) {
  if (!timestamp) {
    return "-";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(date);
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "-";
  }
  return `${Math.round(Number(value) * 100)}%`;
}

function formatDuration(value) {
  if (value == null || value === "") {
    return "-";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return String(value);
  }
  return `${numeric.toFixed(2)} ms`;
}

async function runSampleWorkflow(sampleId, extractorMode, triggerButton = null) {
  setStatus(sampleStatus, "Running sample", "running");
  setSampleRunState(sampleId, true);
  const sampleFamily = sampleId.startsWith("ar_") ? "AR" : "AP";
  const sampleName = visibleDemoCases[sampleId] || sampleId;
  showLoadingCue(buildLoadingStages(`Reading ${sampleFamily} sample`));
  entryWorkflowState.textContent = "Running sample";
  entryWorkflowDetail.textContent = `Processing ${sampleName} through extraction, retrieval, validation, and decisioning.`;
  entryAuditState.textContent = "In progress";
  entryAuditDetail.textContent = "Waiting for recommendation, evidence, review gate, and latency.";

  try {
    const response = await fetch("/workflow/sample", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        sample_id: sampleId,
        extractor_mode: extractorMode
      })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(payload.detail, "Sample workflow failed."));
    }
    renderResult(payload);
    setActiveSample(sampleId);
    setStatus(sampleStatus, "Completed", "success");
    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setStatus(sampleStatus, "Run failed", "error");
    entryWorkflowState.textContent = "Sample failed";
    entryWorkflowDetail.textContent = `${sampleName} could not complete.`;
    entryAuditState.textContent = "Run failed";
    entryAuditDetail.textContent = formatError(error);
    rawJson.textContent = formatError(error);
    setWorkspaceReady();
  } finally {
    setSampleRunState(sampleId, false);
    hideLoadingCue();
    if (triggerButton) {
      triggerButton.blur();
    }
  }
}

function setSampleRunState(sampleId, isRunning) {
  for (const button of sampleRunButtons) {
    const isCurrent = button.dataset.runSample === sampleId;
    button.disabled = isRunning;
    button.textContent = isRunning && isCurrent ? "Running..." : button.dataset.defaultLabel;

    const card = button.closest(".sample-card");
    if (card && isCurrent) {
      card.classList.toggle("is-running", isRunning);
    }
  }
}

function setActiveSample(sampleId) {
  activeSampleId = sampleId;
  for (const button of sampleRunButtons) {
    const isActive = button.dataset.runSample === activeSampleId;
    button.classList.toggle("is-selected", isActive);
    if (isActive) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }

    const card = button.closest(".sample-card");
    if (card) {
      card.classList.toggle("is-selected", isActive);
    }
  }
}

function renderResult(payload) {
  const workflow = payload.workflow_result || {};
  const audit = payload.audit_trail || {};
  const route = payload.route || {};
  const extraction = workflow.extraction || {};
  const policy = payload.policy_assessment || {};
  const apDecision = workflow.ap_decision;
  const arDecision = workflow.ar_decision;
  const finalDecision = apDecision || arDecision || {};
  const evidence = finalDecision.evidence || [];
  const agentTrace = audit.agent_tool_trace || [];
  const workflowHint = payload.workflow_hint ? String(payload.workflow_hint).toUpperCase() : "";

  resultKind.textContent = workflow.workflow_type
    ? `${prettifyWorkflow(workflow.workflow_type)} ready`
    : "No result";
  resultKind.className = workflow.workflow_type ? "status-pill success" : "status-pill neutral";

  routeValue.textContent = prettifyWorkflow(workflow.workflow_type);
  routeReason.textContent = buildRouteExplanation(route, workflow.workflow_type);
  documentValue.textContent = buildDocumentValue(extraction, workflow.workflow_type, payload.source || {});
  documentText.textContent = buildDocumentText(extraction, workflow.workflow_type);

  if (apDecision) {
    decisionValue.textContent = formatRecommendation(apDecision.recommendation);
    decisionSummary.textContent = apDecision.reviewer_summary
      ? `Reason: ${apDecision.reviewer_summary}`
      : "Reason: no reviewer summary was returned.";
    decisionExplainer.textContent = buildDecisionExplanation(apDecision.recommendation, workflow.workflow_type);
    renderTags(anomalyList, (apDecision.anomalies || []).map(mapAnomalyTag), "No anomalies.");
  } else if (arDecision) {
    const arAction = ["medium", "high"].includes(arDecision.escalation_level) ? "escalate" : "draft_follow_up";
    const arSubject = arDecision.subject || arDecision.followup_subject;
    decisionValue.textContent = formatRecommendation(arAction);
    decisionSummary.textContent = arSubject
      ? `Draft subject: ${arSubject}`
      : "Draft subject: no subject generated.";
    decisionExplainer.textContent = buildDecisionExplanation(arDecision.escalation_level, workflow.workflow_type);
    renderTags(anomalyList, (policy.trigger_codes || []).map(mapTriggerTag), "No escalation triggers.");
  } else {
    decisionValue.textContent = "-";
    decisionSummary.textContent = "Run a case to see the recommended action and reason.";
    decisionExplainer.textContent = "The main workflow outcome will be explained here after a run.";
    renderTags(anomalyList, [], "No anomalies.");
  }

  renderTags(signalList, (route.matched_signals || []).map((signal) => ({ text: signal })), "No signals.");
  renderEvidence(evidenceList, evidence);
  renderAgentTrace(agentTraceList, agentTrace);
  renderKeyFields(keyFieldList, extraction, finalDecision.missing_fields || []);
  renderAuditDetails(auditDetailList, audit, finalDecision, evidence);
  renderGuardrailPanel(guardrailPanel, audit, extraction);
  updateFlowMap(extraction, evidence, audit, finalDecision, workflow.workflow_type);
  renderWhyDecision(whyDecisionList, extraction, policy, finalDecision, evidence, audit, workflow.workflow_type);

  evidenceCount.textContent = String(evidence.length);
  evidenceText.textContent = buildEvidenceText(evidence.length);
  updateDecisionSummaryCards(finalDecision, evidence, audit, workflow.workflow_type);

  const auditMeta = buildAuditMeta(finalDecision.confidence, audit);
  auditValue.textContent = auditMeta.title;
  auditText.textContent = workflowHint ? `${auditMeta.body} | Upload hint: ${workflowHint}` : auditMeta.body;
  updateEntryRunSummary(workflow, finalDecision, evidence, audit);

  rawJson.textContent = JSON.stringify(payload, null, 2);
  setWorkspaceReady();
}

function updateFlowMap(extraction, evidence, audit, finalDecision, workflowType) {
  const review = audit.human_review || {};
  const missingFields = Array.isArray(extraction.missing_fields) ? extraction.missing_fields : [];
  const repair = audit.retrieval_repair || {};

  flowExtractionStatus.textContent = missingFields.length ? "Needs field review" : "Schema captured";
  flowExtractionDetail.textContent = buildExtractionFlowDetail(extraction, workflowType, missingFields);

  flowRetrievalStatus.textContent = evidence.length === 1 ? "1 source" : `${evidence.length} sources`;
  flowRetrievalDetail.textContent = buildRetrievalFlowDetail(evidence, repair);

  flowValidationStatus.textContent = review.required ? "Review gate" : "Checks passed";
  flowValidationDetail.textContent = review.required
    ? `${review.blocking ? "Blocking" : "Non-blocking"}: ${(review.reason_codes || []).join(", ") || "policy review"}`
    : "No blocking validation issue was returned.";

  flowDecisionStatus.textContent = buildDecisionFlowStatus(finalDecision, workflowType);
  flowDecisionDetail.textContent = buildDecisionFlowDetail(finalDecision, workflowType);
}

function buildExtractionFlowDetail(extraction, workflowType, missingFields) {
  const party = workflowType === "accounts_receivable"
    ? extraction.customer_name
    : extraction.vendor_name;
  const documentType = prettifyDocumentType(extraction.document_type) || "Finance document";
  const invoice = extraction.invoice_number ? `invoice ${extraction.invoice_number}` : "invoice id pending";
  const missing = missingFields.length ? `Missing: ${missingFields.join(", ")}` : "Required fields are present.";

  return `${documentType} for ${party || "unknown party"} | ${invoice}. ${missing}`;
}

function buildRetrievalFlowDetail(evidence, repair) {
  if (isEvidenceWeak(evidence)) {
    return repair.attempted
      ? "No supporting evidence found after retrieval repair."
      : "Evidence is missing or too weak to support an automatic decision.";
  }

  const repairState = repair.attempted
    ? repair.success ? "repair succeeded" : "repair failed"
    : "direct match";
  const source = evidence[0].source_title || evidence[0].source_id || "policy source";
  return `${source} was the top match; ${repairState}.`;
}

function buildDecisionFlowStatus(finalDecision, workflowType) {
  if (workflowType === "accounts_receivable") {
    const level = finalDecision.escalation_level || "none";
    return level === "none" ? "Draft follow-up" : `${capitalize(level)} escalation`;
  }
  return formatRecommendation(finalDecision.recommendation || "review");
}

function buildDecisionFlowDetail(finalDecision, workflowType) {
  const confidence = finalDecision.confidence == null
    ? "confidence pending"
    : `${Math.round(finalDecision.confidence * 100)}% confidence`;

  if (workflowType === "accounts_receivable") {
    return `${confidence}; ${finalDecision.followup_subject || "follow-up draft ready"}.`;
  }
  return `${confidence}; ${finalDecision.reviewer_summary || "reviewer summary pending"}`;
}

function updateDecisionSummaryCards(finalDecision, evidence, audit, workflowType) {
  const confidence = finalDecision.confidence;
  const risk = buildRiskLabel(finalDecision, audit, workflowType);
  const review = audit.human_review || {};
  const weakEvidence = isEvidenceWeak(evidence);
  const reviewRequired = typeof finalDecision.human_review_required === "boolean"
    ? finalDecision.human_review_required
    : review.required;
  const effectiveReviewRequired = reviewRequired || weakEvidence;
  const evidenceLabel = evidence.length === 1 ? "1 source" : `${evidence.length} sources`;

  confidenceValue.textContent = confidence == null
    ? risk
    : `${Math.round(confidence * 100)}% | ${risk}`;
  riskText.textContent = buildRiskText(risk);

  reviewValue.textContent = effectiveReviewRequired ? "Required" : "Not required";
  reviewText.textContent = weakEvidence
    ? "Required: policy evidence is missing or too weak for an automatic decision."
    : reviewRequired
    ? `${review.blocking ? "Blocking" : "Non-blocking"} review: ${(review.reason_codes || []).join(", ") || "policy check"}`
    : "No human review gate was triggered for this run.";

  decisionEvidenceValue.textContent = evidenceLabel;
  decisionEvidenceText.textContent = weakEvidence
    ? "Weak or missing evidence. Route to human review before acting."
    : evidence.length
    ? `Top cited source: ${evidence[0].source_id}`
    : "No supporting policy evidence was returned.";
}

function renderWhyDecision(container, extraction, policy, finalDecision, evidence, audit, workflowType) {
  container.innerHTML = "";

  if (!workflowType) {
    container.textContent = "Run a workflow to see the policy facts, extracted fields, risk level, and review gate behind the recommendation.";
    container.className = "why-list empty-state";
    return;
  }

  const risk = buildRiskLabel(finalDecision, audit, workflowType);
  const review = audit.human_review || {};
  const weakEvidence = isEvidenceWeak(evidence);
  const reviewRequired = typeof finalDecision.human_review_required === "boolean"
    ? finalDecision.human_review_required
    : review.required;
  const effectiveReviewRequired = reviewRequired || weakEvidence;

  const rows = workflowType === "accounts_payable"
    ? buildApWhyRows(extraction, policy, finalDecision, evidence, risk, effectiveReviewRequired, weakEvidence)
    : buildArWhyRows(extraction, policy, finalDecision, evidence, risk, effectiveReviewRequired, weakEvidence);

  container.className = "why-list";
  for (const row of rows) {
    const item = document.createElement("div");
    item.className = "why-item";

    const label = document.createElement("span");
    label.textContent = row.label;

    const value = document.createElement("strong");
    value.textContent = row.value;

    const note = document.createElement("p");
    note.textContent = row.note;

    item.appendChild(label);
    item.appendChild(value);
    item.appendChild(note);
    container.appendChild(item);
  }
}

function buildApWhyRows(extraction, policy, finalDecision, evidence, risk, reviewRequired, weakEvidence = false) {
  const vendorPolicy = policy.vendor_policy || {};
  const poThreshold = vendorPolicy.po_required_above;
  const poRequired = poThreshold == null || extraction.amount == null
    ? null
    : Number(extraction.amount) > Number(poThreshold);
  const amount = formatAmount(extraction.amount, extraction.currency) || "Unknown";
  const threshold = poThreshold == null
    ? "Policy threshold not found"
    : formatAmount(poThreshold, extraction.currency) || String(poThreshold);
  const topEvidence = evidence[0];

  return [
    {
      label: "PO required?",
      value: poRequired == null ? "Unknown" : poRequired ? "Yes" : "No",
      note: poRequired == null
        ? "No clear PO threshold was available in the retrieved vendor policy."
        : `Vendor policy uses ${threshold} as the PO threshold.`
    },
    {
      label: "PO found?",
      value: extraction.po_number || "No",
      note: extraction.po_number
        ? "The invoice includes a purchase order number."
        : "No purchase order number was extracted from the invoice."
    },
    {
      label: "Invoice amount",
      value: amount,
      note: `Approval threshold checked against ${threshold}.`
    },
    {
      label: "Matching policy",
      value: topEvidence ? topEvidence.source_id : "No citation",
      note: topEvidence ? topEvidence.source_title : "No supporting policy evidence was returned."
    },
    {
      label: "Risk level",
      value: risk,
      note: risk === "High risk"
        ? "The workflow treats this as blocked until review."
        : "Risk is based on review gates and policy checks."
    },
    {
      label: "Recommended action",
      value: formatRecommendation(finalDecision.recommendation),
      note: buildRecommendationMeaning(finalDecision.recommendation, finalDecision.reviewer_summary)
    },
    {
      label: "Human review",
      value: reviewRequired ? "Required" : "Not required",
      note: weakEvidence
        ? "Required because supporting policy evidence is missing or weak."
        : reviewRequired
        ? "A person should review this before payment action."
        : "No human review gate was triggered."
    }
  ];
}

function buildArWhyRows(extraction, policy, finalDecision, evidence, risk, reviewRequired, weakEvidence = false) {
  const triggerCodes = Array.isArray(policy.trigger_codes) ? policy.trigger_codes : [];
  const escalation = finalDecision.escalation_level || "none";
  const topEvidence = evidence[0];
  const amount = formatAmount(extraction.amount, extraction.currency) || "Unknown";

  return [
    {
      label: "Customer / invoice",
      value: [extraction.customer_name, extraction.invoice_number].filter(Boolean).join(" | ") || "Unknown",
      note: `Amount on case: ${amount}.`
    },
    {
      label: "Due date",
      value: extraction.due_date || "Unknown",
      note: "The follow-up is grounded in the extracted receivables case data."
    },
    {
      label: "Escalation level",
      value: capitalize(escalation),
      note: triggerCodes.length
        ? `Triggered by ${triggerCodes.slice(0, 3).join(", ")}.`
        : "No escalation trigger codes were returned."
    },
    {
      label: "Matching policy",
      value: topEvidence ? topEvidence.source_id : "No citation",
      note: topEvidence ? topEvidence.source_title : "No supporting policy evidence was returned."
    },
    {
      label: "Risk level",
      value: risk,
      note: risk === "High risk"
        ? "The workflow treats this as blocked until review."
        : "Risk is based on escalation and review signals."
    },
    {
      label: "Recommended action",
      value: ["medium", "high"].includes(escalation) ? "Escalate" : "Draft Follow-Up",
      note: finalDecision.followup_subject || finalDecision.subject || "No draft subject was returned."
    },
    {
      label: "Human review",
      value: reviewRequired ? "Required" : "Not required",
      note: weakEvidence
        ? "Required because supporting policy evidence is missing or weak."
        : reviewRequired
        ? "A person should review this before sending the follow-up."
        : "No human review gate was triggered."
    }
  ];
}

function isEvidenceWeak(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return true;
  }
  return evidence.some((item) => {
    const sourceId = String(item.source_id || "").trim().toLowerCase();
    const reason = String(item.relevance_reason || "").trim().toLowerCase();
    return !sourceId || sourceId === "uncited" || sourceId === "fallback" || reason.includes("fallback");
  });
}

function buildRecommendationMeaning(recommendation, fallbackSummary) {
  if (recommendation === "missing_info") {
    return "Ask for the missing required details before approving, reviewing, or rejecting the invoice.";
  }
  if (recommendation === "review") {
    return "Send the case to a human reviewer because the invoice may be valid but needs inspection.";
  }
  if (recommendation === "reject") {
    return "Do not proceed with payment unless the issue is corrected and the case is resubmitted.";
  }
  if (recommendation === "approve") {
    return "The invoice can move forward because no blocking issue was found.";
  }
  return fallbackSummary || "No reviewer summary was returned.";
}

function buildRiskLabel(finalDecision, audit, workflowType) {
  if (audit.human_review && audit.human_review.blocking) {
    return "High risk";
  }
  if (audit.human_review && audit.human_review.required) {
    return "Medium risk";
  }
  if (workflowType === "accounts_payable" && finalDecision.recommendation === "approve") {
    return "Low risk";
  }
  if (workflowType === "accounts_receivable" && finalDecision.escalation_level === "none") {
    return "Low risk";
  }
  return "Medium risk";
}

function buildRiskText(risk) {
  if (risk === "High risk") {
    return "Treat this output as blocked until a finance reviewer checks it.";
  }
  if (risk === "Medium risk") {
    return "Review context and evidence before acting on this recommendation.";
  }
  return "The workflow did not find a blocking review condition.";
}

function updateEntryRunSummary(workflow, finalDecision, evidence, audit) {
  const workflowName = prettifyWorkflow(workflow.workflow_type);
  const decision = finalDecision.recommendation || finalDecision.escalation_level || "complete";
  const review = audit.human_review && audit.human_review.required
    ? "review required"
    : "no review gate";
  const latency = audit.total_latency_ms != null ? `${audit.total_latency_ms} ms` : "latency pending";

  entryWorkflowState.textContent = workflowName;
  entryWorkflowDetail.textContent = `Current workflow finished with ${decision}.`;
  entryAuditState.textContent = `${decision} | ${review}`;
  entryAuditDetail.textContent = `${evidence.length} evidence sources | ${latency}`;
}

function renderTags(container, tags, emptyText) {
  container.innerHTML = "";
  if (!tags || tags.length === 0) {
    container.textContent = emptyText;
    container.className = "tag-list empty-state";
    return;
  }

  container.className = "tag-list";
  for (const tag of tags) {
    const span = document.createElement("span");
    span.className = `tag${tag.kind ? ` ${tag.kind}` : ""}`;
    span.textContent = tag.text;
    container.appendChild(span);
  }
}

function renderEvidence(container, evidence) {
  container.innerHTML = "";
  if (!evidence || evidence.length === 0) {
    container.textContent = "No supporting policy evidence was returned. Route this case to review before acting.";
    container.className = "evidence-list empty-state";
    return;
  }

  container.className = "evidence-list";
  for (const item of evidence) {
    const card = document.createElement("article");
    card.className = "evidence-item";

    const meta = document.createElement("div");
    meta.className = "evidence-meta";

    const source = document.createElement("span");
    source.textContent = `Source: ${extractEvidenceSourceName(item)}`;

    const citation = document.createElement("span");
    citation.textContent = `Citation: ${item.source_id || "uncited"}`;

    meta.appendChild(source);
    meta.appendChild(citation);

    const title = document.createElement("strong");
    title.textContent = extractEvidenceRuleName(item);

    const excerpt = document.createElement("p");
    excerpt.className = "evidence-excerpt";
    excerpt.textContent = item.excerpt;

    const detailList = document.createElement("dl");
    detailList.className = "evidence-details";
    appendEvidenceDetail(detailList, "Decision impact", inferEvidenceInfluence(item));
    appendEvidenceDetail(detailList, "Why relevant", item.relevance_reason || "Supports this workflow decision.");

    card.appendChild(meta);
    card.appendChild(title);
    card.appendChild(excerpt);
    card.appendChild(detailList);
    container.appendChild(card);
  }
}

function extractEvidenceSourceName(item) {
  const title = item.source_title || "";
  if (!title) {
    return "Policy source";
  }
  return title.split(" - ")[0] || title;
}

function extractEvidenceRuleName(item) {
  const title = item.source_title || "";
  if (title.includes(" - ")) {
    return title.split(" - ").slice(1).join(" - ");
  }
  return item.source_id ? `Policy Match ${item.source_id}` : "Policy match";
}

function appendEvidenceDetail(list, label, value) {
  const group = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");

  term.textContent = label;
  description.textContent = value;

  group.appendChild(term);
  group.appendChild(description);
  list.appendChild(group);
}

function inferEvidenceInfluence(item) {
  const sourceId = item.source_id || "";
  const reason = (item.relevance_reason || "").toLowerCase();

  if (sourceId.startsWith("VENDOR-")) {
    return "Vendor-specific policy check";
  }
  if (sourceId.startsWith("CUSTOMER-")) {
    return "Customer-specific follow-up context";
  }
  if (sourceId.includes("APPROVAL")) {
    return reason.includes("po") ? "PO and approval requirement check" : "Approval threshold check";
  }
  if (sourceId.includes("POLICY")) {
    return "Invoice validation policy";
  }
  if (sourceId.includes("ESCALATION")) {
    return "AR escalation decision";
  }
  if (sourceId.includes("TEMPLATE")) {
    return "Follow-up draft guidance";
  }
  return "Decision support";
}

function renderAgentTrace(container, traces) {
  container.innerHTML = "";
  if (!traces || traces.length === 0) {
    container.textContent = "No tool calls returned.";
    container.className = "evidence-list empty-state";
    return;
  }

  container.className = "evidence-list";
  for (const trace of traces) {
    const card = document.createElement("article");
    card.className = "evidence-item";

    const title = document.createElement("strong");
    title.textContent = trace.tool_name || "unknown_tool";

    const summary = document.createElement("p");
    summary.textContent = trace.output_summary || trace.purpose || "";

    const reason = document.createElement("small");
    const review = trace.requires_human_review ? "review required" : "auto";
    const confidence = trace.confidence_signal || "unknown";
    reason.textContent = `${confidence} | ${review}`;

    card.appendChild(title);
    card.appendChild(summary);
    card.appendChild(reason);
    container.appendChild(card);
  }
}

function renderKeyFields(container, extraction, decisionMissingFields = []) {
  container.innerHTML = "";
  const missingFields = decisionMissingFields.length
    ? decisionMissingFields
    : extraction.missing_fields || [];

  const entries = [
    ["Document type", prettifyDocumentType(extraction.document_type)],
    ["Vendor", extraction.vendor_name],
    ["Customer", extraction.customer_name],
    ["Invoice number", extraction.invoice_number],
    ["PO number", extraction.po_number],
    ["Amount", formatAmount(extraction.amount, extraction.currency)],
    ["Due date", extraction.due_date],
    ["Payment terms", extraction.payment_terms],
    [
      "Missing fields",
      Array.isArray(missingFields) && missingFields.length
        ? missingFields.join(", ")
        : null
    ]
  ].filter((entry) => entry[1]);

  if (entries.length === 0) {
    container.textContent = "No extracted fields yet.";
    container.className = "key-field-list empty-state";
    return;
  }

  container.className = "key-field-list";
  for (const [label, value] of entries) {
    const card = document.createElement("article");
    card.className = "key-field-item";

    const heading = document.createElement("span");
    heading.className = "key-field-label";
    heading.textContent = label;

    const body = document.createElement("strong");
    body.className = "key-field-value";
    body.textContent = value;

    card.appendChild(heading);
    card.appendChild(body);
    container.appendChild(card);
  }
}

function renderAuditDetails(container, audit, finalDecision, evidence) {
  container.innerHTML = "";

  const review = audit.human_review || {};
  const entries = [
    ["Prompt version", audit.prompt_version],
    ["Extractor mode", audit.effective_extractor_mode],
    ["Confidence", finalDecision.confidence == null ? null : `${Math.round(finalDecision.confidence * 100)}%`],
    ["Human review", review.required ? (review.blocking ? "Blocking review" : "Review required") : "Not required"],
    ["Evidence", evidence.length ? `${evidence.length} sources` : "No evidence"],
    ["Tool calls", Array.isArray(audit.agent_tool_trace) ? String(audit.agent_tool_trace.length) : null],
    ["Latency", audit.total_latency_ms == null ? null : `${audit.total_latency_ms} ms`],
    [
      "RAG repair",
      audit.retrieval_repair && audit.retrieval_repair.attempted
        ? audit.retrieval_repair.success ? "Succeeded" : "Failed"
        : "Not needed"
    ],
    ["LLM gateway", Array.isArray(audit.llm_gateway) ? `${audit.llm_gateway.length} calls` : null]
  ].filter((entry) => entry[1]);

  if (entries.length === 0) {
    container.textContent = "No audit metadata yet.";
    container.className = "key-field-list empty-state";
    return;
  }

  container.className = "key-field-list";
  for (const [label, value] of entries) {
    const card = document.createElement("article");
    card.className = "key-field-item";

    const heading = document.createElement("span");
    heading.className = "key-field-label";
    heading.textContent = label;

    const body = document.createElement("strong");
    body.className = "key-field-value";
    body.textContent = value;

    card.appendChild(heading);
    card.appendChild(body);
    container.appendChild(card);
  }
}

function renderGuardrailPanel(container, audit, extraction) {
  if (!container) {
    return;
  }

  container.innerHTML = "";

  const gatewayCalls = Array.isArray(audit.llm_gateway) ? audit.llm_gateway : [];
  const latestGateway = gatewayCalls[gatewayCalls.length - 1] || {};
  const stageLatencies = audit.stage_latencies_ms || {};
  const repair = audit.retrieval_repair || {};
  const extractionWarnings = extraction.extraction_warnings || [];
  const missingFields = extraction.missing_fields || [];
  const tokenTotal = gatewayCalls.reduce((sum, call) => sum + Number(call.total_tokens || 0), 0);
  const redactionCounts = gatewayCalls.reduce(
    (counts, call) => {
      const redactions = call.redaction_counts || {};
      counts.emails += Number(redactions.emails || 0);
      counts.phones += Number(redactions.phones || 0);
      return counts;
    },
    { emails: 0, phones: 0 }
  );

  const cards = [
    {
      label: "Prompt version",
      value: audit.prompt_version || "Not reported",
      detail: audit.repair_prompt_version
        ? `Repair prompt: ${audit.repair_prompt_version}`
        : "Extractor prompt version appears here when reported."
    },
    {
      label: "Extractor mode",
      value: audit.effective_extractor_mode || "Unknown",
      detail: audit.requested_extractor_mode && audit.requested_extractor_mode !== audit.effective_extractor_mode
        ? `Requested ${audit.requested_extractor_mode}, then used ${audit.effective_extractor_mode}.`
        : `Prompt applied: ${audit.prompt_applied ? "yes" : "no; deterministic fallback or heuristic mode."}`
    },
    {
      label: "Schema validation",
      value: missingFields.length ? "Passed with missing fields" : "Passed",
      detail: extractionWarnings.length
        ? `${extractionWarnings.length} extraction warnings: ${extractionWarnings.slice(0, 2).join(", ")}`
        : "The backend returned a structured extraction object for this case."
    },
    {
      label: "Repair attempted",
      value: repair.attempted ? (repair.success ? "Succeeded" : "Failed") : "Not needed",
      detail: repair.reason || "Retrieval repair only runs when supporting evidence is weak or missing."
    },
    {
      label: "PII redaction",
      value: gatewayCalls.length ? `${redactionCounts.emails + redactionCounts.phones} items` : "No live call",
      detail: gatewayCalls.length
        ? `${redactionCounts.emails} emails and ${redactionCounts.phones} phones redacted before gateway calls.`
        : "No gateway metadata was recorded for this deterministic/demo run."
    },
    {
      label: "LLM gateway calls",
      value: String(gatewayCalls.length),
      detail: latestGateway.model
        ? `${latestGateway.model} | ${latestGateway.response_format || "response format unknown"}`
        : "Live LLM mode records model and response-format metadata here."
    },
    {
      label: "Latency by stage",
      value: audit.total_latency_ms == null ? "Not reported" : `${audit.total_latency_ms} ms total`,
      detail: formatStageLatencyDetail(stageLatencies)
    },
    {
      label: "Token / cost metadata",
      value: tokenTotal ? `${tokenTotal} tokens` : "Not available",
      detail: tokenTotal
        ? "Token counts are recorded when the configured gateway provider returns usage data."
        : "Demo mode avoids paid gateway usage, so cost metadata is intentionally absent."
    }
  ];

  for (const cardData of cards) {
    const card = document.createElement("article");
    card.className = "guardrail-item";

    const label = document.createElement("span");
    label.textContent = cardData.label;

    const value = document.createElement("strong");
    value.textContent = cardData.value;

    const detail = document.createElement("p");
    detail.textContent = cardData.detail;

    card.appendChild(label);
    card.appendChild(value);
    card.appendChild(detail);
    container.appendChild(card);
  }
}

function formatStageLatencyDetail(stageLatencies) {
  const entries = Object.entries(stageLatencies || {}).filter(([, value]) => value != null);
  if (entries.length === 0) {
    return "Stage-level latency was not reported for this run.";
  }

  return entries
    .map(([label, value]) => `${label.replaceAll("_", " ")}: ${value} ms`)
    .join(" | ");
}

function setStatus(node, text, kind) {
  node.textContent = text;
  node.className = `status-pill${kind ? ` ${kind}` : ""}`;
}

function mapAnomalyTag(anomaly) {
  const severity = (anomaly.severity || "").toLowerCase();
  let kind = "";
  if (severity === "high") {
    kind = "error";
  } else if (severity === "medium" || severity === "low") {
    kind = "warning";
  }
  return {
    text: `${anomaly.code}: ${anomaly.message}`,
    kind
  };
}

function mapTriggerTag(trigger) {
  const kind = trigger.includes("high")
    ? "error"
    : trigger.includes("medium") || trigger.includes("low")
      ? "warning"
      : "";
  return { text: trigger, kind };
}

function prettifyWorkflow(value) {
  if (!value) {
    return "-";
  }
  if (value === "accounts_payable") {
    return "Accounts Payable";
  }
  if (value === "accounts_receivable") {
    return "Accounts Receivable";
  }
  return value;
}

function prettifyDocumentType(value) {
  if (!value) {
    return "-";
  }
  if (value === "invoice") {
    return "Invoice";
  }
  if (value === "overdue_email") {
    return "Overdue email";
  }
  if (value === "payment_confirmation") {
    return "Payment confirmation";
  }
  return value;
}

function capitalize(value) {
  if (!value) {
    return "";
  }
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function formatRecommendation(value) {
  if (!value) {
    return "-";
  }
  const labels = {
    approve: "Approve",
    review: "Human Review",
    reject: "Reject / Do Not Proceed",
    missing_info: "Request Missing Info",
    escalate: "Escalate",
    draft_follow_up: "Draft Follow-Up"
  };
  return labels[value] || value;
}

function buildAuditMeta(confidence, audit) {
  const titleParts = [];
  const bodyParts = [];

  if (audit.prompt_version) {
    const mode = audit.effective_extractor_mode ? ` (${audit.effective_extractor_mode})` : "";
    titleParts.push(`${audit.prompt_version}${mode}`);
  }
  if (audit.total_latency_ms != null) {
    bodyParts.push(`Completed in ${audit.total_latency_ms} ms`);
  }
  if (confidence != null) {
    bodyParts.push(`Confidence ${confidence}`);
  }
  if (Array.isArray(audit.agent_tool_trace)) {
    bodyParts.push(`${audit.agent_tool_trace.length} tool calls`);
  }
  if (audit.retrieval_repair && audit.retrieval_repair.attempted) {
    bodyParts.push(audit.retrieval_repair.success ? "RAG repaired" : "RAG repair failed");
  }
  if (Array.isArray(audit.llm_gateway) && audit.llm_gateway.length) {
    bodyParts.push(`${audit.llm_gateway.length} gateway calls`);
  }
  if (audit.human_review && audit.human_review.required) {
    bodyParts.push(audit.human_review.blocking ? "Blocking review" : "Review gate");
  }
  if (audit.requested_extractor_mode && audit.requested_extractor_mode !== audit.effective_extractor_mode) {
    bodyParts.push(`Requested ${audit.requested_extractor_mode}, switched to ${audit.effective_extractor_mode}`);
  }

  return {
    title: titleParts.length ? titleParts.join(" | ") : "No metadata yet",
    body: bodyParts.length ? bodyParts.join(" | ") : "Latency, prompt version, and confidence will appear here."
  };
}

function buildRouteExplanation(route, workflowType) {
  if (!workflowType) {
    return "Run a sample or upload a file to see the workflow route.";
  }

  const intro = workflowType === "accounts_payable"
    ? "This document was treated as an invoice review flow."
    : "This document was treated as a receivables follow-up flow.";

  if (!route.reason) {
    return intro;
  }
  return `${intro} ${route.reason}`;
}

function buildDocumentValue(extraction, workflowType, source) {
  const primary = workflowType === "accounts_payable"
    ? extraction.vendor_name
    : extraction.customer_name;
  const secondary = extraction.invoice_number;
  const joined = [primary, secondary].filter(Boolean).join(" | ");
  return joined || source.filename || "Document not identified yet";
}

function buildDocumentText(extraction, workflowType) {
  if (!workflowType) {
    return "The key invoice or customer details will appear here.";
  }

  if (workflowType === "accounts_payable") {
    return extraction.po_number
      ? "Vendor, invoice, and purchase-order fields were extracted for the AP review path."
      : "Vendor and invoice fields were extracted, and the AP path will use them to check approval policy.";
  }

  return "Customer, invoice, due-date, and payment context fields were extracted for the AR follow-up path.";
}

function buildEvidenceText(count) {
  if (!count) {
    return "Supporting policy evidence will appear after a run.";
  }
  if (count === 1) {
    return "One policy source is supporting this workflow result.";
  }
  return `${count} policy sources are supporting this workflow result.`;
}

function buildDecisionExplanation(value, workflowType) {
  if (!value || !workflowType) {
    return "The main workflow outcome will be explained here after a run.";
  }

  if (workflowType === "accounts_payable") {
    if (value === "approve") {
      return "The system believes the invoice can move forward without extra intervention.";
    }
    if (value === "review") {
      return "Human review means the invoice may still be valid, but a person must inspect policy, evidence, or risk signals before payment continues.";
    }
    if (value === "reject") {
      return "Reject means the invoice should not move forward in its current state because the workflow found a likely invalid or unsupported case.";
    }
    if (value === "missing_info") {
      return "Request missing info means the invoice is not being rejected; the safest next step is to ask for the required details before deciding.";
    }
  }

  if (value === "none") {
    return "The system recommends a friendly reminder rather than an escalated collections-style message.";
  }
  if (value === "low") {
    return "The system recommends a light escalation because the case needs follow-up but is not yet severe.";
  }
  if (value === "medium") {
    return "The system recommends a firmer follow-up because the case is more overdue or has repeated reminders.";
  }
  if (value === "high") {
    return "The system recommends urgent follow-up because the case is significantly overdue.";
  }

  return "The system has produced a workflow outcome for this case.";
}

function formatAmount(amount, currency) {
  if (amount == null) {
    return "";
  }
  return [currency, Number(amount).toFixed(2)].filter(Boolean).join(" ");
}

function formatError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function formatApiError(detail, fallback) {
  if (!detail) {
    return fallback;
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (typeof detail === "object") {
    const message = detail.message || fallback;
    const helperParts = [];

    if (Array.isArray(detail.allowed_extensions) && detail.allowed_extensions.length) {
      helperParts.push(`Allowed: ${detail.allowed_extensions.join(", ")}`);
    }
    if (Array.isArray(detail.allowed) && detail.allowed.length) {
      helperParts.push(`Allowed: ${detail.allowed.join(", ")}`);
    }
    if (detail.ocr_note) {
      helperParts.push(detail.ocr_note);
    }
    if (detail.fallback) {
      helperParts.push(detail.fallback);
    }

    return helperParts.length ? `${message} ${helperParts.join(" ")}` : message;
  }

  return fallback;
}
