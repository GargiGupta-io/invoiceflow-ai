const sampleForm = document.getElementById("sample-form");
const uploadForm = document.getElementById("upload-form");
const sampleSelect = document.getElementById("sample-select");
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
const evidenceCount = document.getElementById("evidence-count");
const evidenceText = document.getElementById("evidence-text");
const auditValue = document.getElementById("audit-value");
const auditText = document.getElementById("audit-text");
const anomalyList = document.getElementById("anomaly-list");
const signalList = document.getElementById("signal-list");
const evidenceList = document.getElementById("evidence-list");
const agentTraceList = document.getElementById("agent-trace-list");
const keyFieldList = document.getElementById("key-field-list");
const rawJson = document.getElementById("raw-json");
const heroSampleButtons = document.querySelectorAll("[data-run-sample]");

bootstrap();

for (const button of heroSampleButtons) {
  button.addEventListener("click", () => {
    const sampleId = button.dataset.runSample;
    const sampleMode = document.getElementById("sample-mode");
    if (sampleId) {
      sampleSelect.value = sampleId;
      runSampleWorkflow(sampleId, sampleMode.value);
    }
  });
}

async function bootstrap() {
  setStatus(sampleStatus, "Loading samples", "running");
  try {
    const response = await fetch("/samples");
    const payload = await response.json();
    const samples = payload.samples || [];
    populateSamples(samples);
    applyQueryDefaults(samples);
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

  await runSampleWorkflow(sampleId, extractorMode);
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

function applyQueryDefaults(samples) {
  const params = new URLSearchParams(window.location.search);
  const requestedSample = params.get("sample");
  const requestedMode = params.get("mode");
  const autorun = params.get("autorun");
  const sampleMode = document.getElementById("sample-mode");

  if (requestedSample && samples.some((sample) => sample.sample_id === requestedSample)) {
    sampleSelect.value = requestedSample;
  }

  if (requestedMode && ["heuristic", "auto", "llm"].includes(requestedMode)) {
    sampleMode.value = requestedMode;
  }

  if (autorun === "1" && sampleSelect.value) {
    runSampleWorkflow(sampleSelect.value, sampleMode.value);
  }
}

async function runSampleWorkflow(sampleId, extractorMode) {
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

  resultKind.textContent = workflow.workflow_type
    ? `${prettifyWorkflow(workflow.workflow_type)} ready`
    : "No result";
  resultKind.className = workflow.workflow_type ? "status-pill success" : "status-pill neutral";

  routeValue.textContent = prettifyWorkflow(workflow.workflow_type);
  routeReason.textContent = buildRouteExplanation(route, workflow.workflow_type);
  documentValue.textContent = buildDocumentValue(extraction, workflow.workflow_type, payload.source || {});
  documentText.textContent = buildDocumentText(extraction, workflow.workflow_type);

  if (apDecision) {
    decisionValue.textContent = apDecision.recommendation || "-";
    decisionSummary.textContent = apDecision.reviewer_summary || "No reviewer summary available.";
    decisionExplainer.textContent = buildDecisionExplanation(apDecision.recommendation, workflow.workflow_type);
    renderTags(anomalyList, (apDecision.anomalies || []).map(mapAnomalyTag), "No anomalies.");
  } else if (arDecision) {
    decisionValue.textContent = arDecision.escalation_level || "-";
    decisionSummary.textContent = arDecision.followup_subject || "No subject generated.";
    decisionExplainer.textContent = buildDecisionExplanation(arDecision.escalation_level, workflow.workflow_type);
    renderTags(anomalyList, (policy.trigger_codes || []).map(mapTriggerTag), "No escalation triggers.");
  } else {
    decisionValue.textContent = "-";
    decisionSummary.textContent = "No final decision payload returned.";
    decisionExplainer.textContent = "The main workflow outcome will be explained here after a run.";
    renderTags(anomalyList, [], "No anomalies.");
  }

  renderTags(signalList, (route.matched_signals || []).map((signal) => ({ text: signal })), "No signals.");
  renderEvidence(evidenceList, evidence);
  renderAgentTrace(agentTraceList, agentTrace);
  renderKeyFields(keyFieldList, extraction);

  evidenceCount.textContent = String(evidence.length);
  evidenceText.textContent = buildEvidenceText(evidence.length);

  const auditMeta = buildAuditMeta(finalDecision.confidence, audit);
  auditValue.textContent = auditMeta.title;
  auditText.textContent = auditMeta.body;

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
    title.textContent = `${item.source_id} - ${item.source_title}`;

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

function renderKeyFields(container, extraction) {
  container.innerHTML = "";

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
      Array.isArray(extraction.missing_fields) && extraction.missing_fields.length
        ? extraction.missing_fields.join(", ")
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
      return "The system found something that should be checked by a person before payment continues.";
    }
    if (value === "reject") {
      return "The system believes the invoice should not move forward in its current state.";
    }
    if (value === "missing_info") {
      return "The system believes the safest next step is to request missing details before continuing.";
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
