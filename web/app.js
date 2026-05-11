const sampleForm = document.getElementById("sample-form");
const uploadForm = document.getElementById("upload-form");
const sampleSelect = document.getElementById("sample-select");
const sampleStatus = document.getElementById("sample-status");
const uploadStatus = document.getElementById("upload-status");
const resultKind = document.getElementById("result-kind");
const routeValue = document.getElementById("route-value");
const routeReason = document.getElementById("route-reason");
const decisionValue = document.getElementById("decision-value");
const decisionSummary = document.getElementById("decision-summary");
const evidenceCount = document.getElementById("evidence-count");
const confidenceText = document.getElementById("confidence-text");
const anomalyList = document.getElementById("anomaly-list");
const signalList = document.getElementById("signal-list");
const evidenceList = document.getElementById("evidence-list");
const rawJson = document.getElementById("raw-json");

bootstrap();

async function bootstrap() {
  setStatus(sampleStatus, "Loading samples", "running");
  try {
    const response = await fetch("/samples");
    const payload = await response.json();
    populateSamples(payload.samples || []);
    setStatus(sampleStatus, "Ready", "success");
  } catch (error) {
    setStatus(sampleStatus, "Failed to load samples", "error");
    rawJson.textContent = formatError(error);
  }
}

sampleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const sampleId = sampleSelect.value;
  const extractorMode = document.getElementById("sample-mode").value;

  if (!sampleId) {
    setStatus(sampleStatus, "Select a sample first", "error");
    return;
  }

  setStatus(sampleStatus, "Running sample", "running");
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
      throw new Error(payload.detail || "Sample workflow failed.");
    }
    renderResult(payload);
    setStatus(sampleStatus, "Completed", "success");
  } catch (error) {
    setStatus(sampleStatus, "Run failed", "error");
    rawJson.textContent = formatError(error);
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("upload-file");
  const extractorMode = document.getElementById("upload-mode").value;

  if (!fileInput.files || fileInput.files.length === 0) {
    setStatus(uploadStatus, "Choose a file first", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("extractor_mode", extractorMode);

  setStatus(uploadStatus, "Uploading", "running");
  try {
    const response = await fetch("/workflow/upload", {
      method: "POST",
      body: formData
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Upload workflow failed.");
    }
    renderResult(payload);
    setStatus(uploadStatus, "Completed", "success");
  } catch (error) {
    setStatus(uploadStatus, "Run failed", "error");
    rawJson.textContent = formatError(error);
  }
});

function populateSamples(samples) {
  sampleSelect.innerHTML = "";
  for (const sample of samples) {
    const option = document.createElement("option");
    option.value = sample.sample_id;
    option.textContent = `${sample.sample_id} (${sample.category})`;
    sampleSelect.appendChild(option);
  }
}

function renderResult(payload) {
  const workflow = payload.workflow_result || {};
  const audit = payload.audit_trail || {};
  const route = payload.route || {};
  const context = payload.grounded_context || {};
  const policy = payload.policy_assessment || {};
  const apDecision = workflow.ap_decision;
  const arDecision = workflow.ar_decision;
  const finalDecision = apDecision || arDecision || {};
  const evidence = finalDecision.evidence || [];

  resultKind.textContent = workflow.workflow_type || "Unknown";
  resultKind.className = "status-pill success";

  routeValue.textContent = prettifyWorkflow(workflow.workflow_type);
  routeReason.textContent = route.reason || "No route reason available.";

  if (apDecision) {
    decisionValue.textContent = apDecision.recommendation || "-";
    decisionSummary.textContent = apDecision.reviewer_summary || "No reviewer summary available.";
    renderTags(anomalyList, (apDecision.anomalies || []).map(mapAnomalyTag), "No anomalies.");
  } else if (arDecision) {
    decisionValue.textContent = arDecision.escalation_level || "-";
    decisionSummary.textContent = arDecision.followup_subject || "No subject generated.";
    renderTags(anomalyList, (policy.trigger_codes || []).map(mapTriggerTag), "No escalation triggers.");
  } else {
    decisionValue.textContent = "-";
    decisionSummary.textContent = "No final decision payload returned.";
    renderTags(anomalyList, [], "No anomalies.");
  }

  renderTags(signalList, (route.matched_signals || []).map((signal) => ({ text: signal })), "No signals.");
  renderEvidence(evidenceList, evidence);

  evidenceCount.textContent = String(evidence.length);
  confidenceText.textContent = buildAuditMeta(finalDecision.confidence, audit);

  rawJson.textContent = JSON.stringify(payload, null, 2);
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
    container.textContent = "No evidence returned.";
    container.className = "evidence-list empty-state";
    return;
  }

  container.className = "evidence-list";
  for (const item of evidence) {
    const card = document.createElement("article");
    card.className = "evidence-item";

    const title = document.createElement("strong");
    title.textContent = `${item.source_id} — ${item.source_title}`;

    const excerpt = document.createElement("p");
    excerpt.textContent = item.excerpt;

    const reason = document.createElement("small");
    reason.textContent = item.relevance_reason;

    card.appendChild(title);
    card.appendChild(excerpt);
    card.appendChild(reason);
    container.appendChild(card);
  }
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
  const kind = trigger.includes("high") ? "error" : trigger.includes("medium") || trigger.includes("low") ? "warning" : "";
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

function buildAuditMeta(confidence, audit) {
  const parts = [];
  if (confidence != null) {
    parts.push(`Confidence ${confidence}`);
  }
  if (audit.total_latency_ms != null) {
    parts.push(`Latency ${audit.total_latency_ms} ms`);
  }
  if (audit.prompt_version) {
    const mode = audit.effective_extractor_mode ? ` (${audit.effective_extractor_mode})` : "";
    parts.push(`Prompt ${audit.prompt_version}${mode}`);
  }
  if (parts.length === 0) {
    return "No confidence returned.";
  }
  return parts.join(" | ");
}

function formatError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
