import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  History,
  LoaderCircle,
  RefreshCw,
  ShieldAlert
} from "lucide-react";

import {
  createReviewDecision,
  getTenantDocument,
  listDocumentAudit,
  listDocumentPages,
  requestDocumentAccess,
  ReviewerApiError
} from "./api.js";

const NOOP = () => {};

const REVIEW_ACTIONS = [
  { value: "approved", label: "Approve" },
  { value: "returned_for_info", label: "Request info" },
  { value: "rejected", label: "Reject" },
  { value: "escalated", label: "Escalate" }
];

const RECOMMENDATION_LABELS = {
  approve: "Approve",
  review: "Human review",
  reject: "Reject",
  missing_info: "Request missing info"
};

const REASON_LABELS = {
  ap_missing_info: "Missing invoice information",
  ap_reject: "Invoice rejection signal",
  ap_review: "Manual AP review",
  approval_threshold: "Approval threshold exceeded",
  duplicate_invoice: "Possible duplicate invoice",
  low_confidence: "Low extraction confidence",
  manual_threshold_review: "Manager approval required",
  missing_extracted_fields: "Required fields were not found",
  missing_policy_evidence: "Policy evidence was not found",
  payment_claim_without_proof: "Payment claimed without proof",
  po_required_missing: "Missing purchase order"
};

const AUDIT_LABELS = {
  "document.uploaded": "Document uploaded",
  "document.processing_requested": "Processing requested",
  "document.processing_dispatched": "Sent to processing queue",
  "document.processing_started": "Extraction started",
  "document.processing_completed": "Extraction completed",
  "document.access_url_issued": "Private document link issued",
  "review.approved": "Reviewer approved case",
  "review.rejected": "Reviewer rejected case",
  "review.returned_for_info": "Reviewer requested information",
  "review.escalated": "Reviewer escalated case"
};

function humanize(value) {
  if (!value) return "Not available";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function reasonLabel(value) {
  return REASON_LABELS[value] || humanize(value);
}

function formatGmt(value) {
  if (!value) return "Time unavailable";
  const formatted = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC"
  }).format(new Date(value));
  return `${formatted} GMT`;
}

function formatAmount(amount, currency) {
  if (amount === null || amount === undefined) return "Not found";
  try {
    return new Intl.NumberFormat("en", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2
    }).format(amount);
  } catch {
    return `${currency || ""} ${amount}`.trim();
  }
}

function recommendationFor(caseResult) {
  const workflow = caseResult?.workflow_result || {};
  if (workflow.ap_decision) {
    return {
      label: RECOMMENDATION_LABELS[workflow.ap_decision.recommendation] || humanize(workflow.ap_decision.recommendation),
      summary: workflow.ap_decision.reviewer_summary,
      confidence: workflow.ap_decision.confidence,
      humanReviewRequired: workflow.ap_decision.human_review_required,
      decision: workflow.ap_decision
    };
  }
  if (workflow.ar_decision) {
    return {
      label: "Draft follow-up",
      summary: workflow.ar_decision.subject || workflow.ar_decision.followup_subject,
      confidence: workflow.ar_decision.confidence,
      humanReviewRequired: workflow.ar_decision.human_review_required,
      decision: workflow.ar_decision
    };
  }
  return null;
}

function defaultAction(recommendation) {
  const normalized = recommendation?.decision?.recommendation;
  if (normalized === "approve") return "approved";
  if (normalized === "missing_info") return "returned_for_info";
  if (normalized === "reject") return "rejected";
  return "escalated";
}

function CaseLoading() {
  return (
    <div className="case-state" role="status">
      <LoaderCircle className="spin" size={22} aria-hidden="true" />
      Loading protected case details...
    </div>
  );
}

export default function CaseDetail({
  accessToken,
  documentId,
  fetchImpl = fetch,
  onBack,
  onSessionInvalid = NOOP
}) {
  const [caseState, setCaseState] = useState("loading");
  const [caseError, setCaseError] = useState("");
  const [detail, setDetail] = useState(null);
  const [pages, setPages] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [accessLink, setAccessLink] = useState(null);
  const [accessBusy, setAccessBusy] = useState(false);
  const [reviewAction, setReviewAction] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewNotice, setReviewNotice] = useState(null);

  const handleError = useCallback((error, fallback) => {
    if (error instanceof ReviewerApiError && error.status === 401) {
      onSessionInvalid();
      return "Your reviewer session expired. Sign in again.";
    }
    return error instanceof Error ? error.message : fallback;
  }, [onSessionInvalid]);

  const loadCase = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setCaseState("loading");
      setCaseError("");
    }
    try {
      const [nextDetail, pagePayload, nextAudit] = await Promise.all([
        getTenantDocument(accessToken, documentId, fetchImpl),
        listDocumentPages(accessToken, documentId, fetchImpl),
        listDocumentAudit(accessToken, documentId, fetchImpl)
      ]);
      setDetail(nextDetail);
      setPages(pagePayload.items || []);
      setAuditEvents(nextAudit || []);
      setCaseState("ready");
    } catch (error) {
      setCaseError(handleError(error, "The protected case could not be loaded."));
      setCaseState("error");
    }
  }, [accessToken, documentId, fetchImpl, handleError]);

  useEffect(() => {
    setAccessLink(null);
    setReviewNotice(null);
    loadCase();
  }, [loadCase]);

  const caseResult = detail?.case_result;
  const workflow = caseResult?.workflow_result || {};
  const extraction = workflow.extraction || {};
  const recommendation = useMemo(() => recommendationFor(caseResult), [caseResult]);
  const latestJob = detail?.processing_jobs?.[0];
  const reviewGate = caseResult?.human_review || {};
  const reasons = reviewGate.reason_codes || [];
  const risk = reviewGate.blocking ? "High risk" : reviewGate.required ? "Needs review" : "Low risk";
  const pageCount = detail?.document.page_count || pages.length;

  useEffect(() => {
    if (!recommendation || reviewAction) return;
    setReviewAction(defaultAction(recommendation));
    setReviewReason(recommendation.summary || reviewGate.reviewer_prompt || "Finance review completed.");
  }, [recommendation, reviewAction, reviewGate.reviewer_prompt]);

  const facts = [
    ["Vendor", extraction.vendor_name],
    ["Customer", extraction.customer_name],
    ["Invoice number", extraction.invoice_number],
    ["Amount", formatAmount(extraction.amount, extraction.currency)],
    ["Due date", extraction.due_date],
    ["Purchase order", extraction.po_number]
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");

  async function prepareAccess() {
    setAccessBusy(true);
    setReviewNotice(null);
    try {
      const receipt = await requestDocumentAccess(accessToken, documentId, fetchImpl);
      setAccessLink(receipt);
    } catch (error) {
      setReviewNotice({ tone: "danger", message: handleError(error, "Private access could not be prepared.") });
    } finally {
      setAccessBusy(false);
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    if (!caseResult?.processing_job_id || !reviewAction || !reviewReason.trim()) return;
    setReviewBusy(true);
    setReviewNotice(null);
    try {
      await createReviewDecision(
        accessToken,
        documentId,
        {
          processing_job_id: caseResult.processing_job_id,
          action: reviewAction,
          reason: reviewReason.trim(),
          reviewer_note: reviewNote.trim() || null
        },
        fetchImpl
      );
      setReviewNote("");
      setReviewNotice({ tone: "success", message: "Review decision saved to the case audit history." });
      await loadCase({ silent: true });
    } catch (error) {
      setReviewNotice({ tone: "danger", message: handleError(error, "The review decision could not be saved.") });
    } finally {
      setReviewBusy(false);
    }
  }

  if (caseState === "loading") return <CaseLoading />;

  if (caseState === "error") {
    return (
      <div className="case-state case-error" role="alert">
        <ShieldAlert size={22} aria-hidden="true" />
        <span>{caseError}</span>
        <button type="button" onClick={() => loadCase()}>Try again</button>
        <button type="button" onClick={onBack}>Back to history</button>
      </div>
    );
  }

  return (
    <section className="case-detail" aria-labelledby="case-detail-title">
      <div className="case-toolbar">
        <button className="icon-text-button" type="button" onClick={onBack}>
          <ArrowLeft size={17} aria-hidden="true" /> Back to history
        </button>
        <button className="icon-text-button" type="button" onClick={() => loadCase()}>
          <RefreshCw size={17} aria-hidden="true" /> Refresh case
        </button>
      </div>

      <header className="case-heading">
        <div>
          <p className="eyebrow">Protected case · {humanize(workflow.workflow_type || detail.document.status)}</p>
          <h2 id="case-detail-title">{detail.document.original_filename}</h2>
          <p>Case {detail.document.id.slice(0, 8)} · {pageCount ? `${pageCount} ${pageCount === 1 ? "page" : "pages"}` : "Page count pending"}</p>
        </div>
        <span className={`risk-badge risk-${risk === "High risk" ? "high" : risk === "Needs review" ? "medium" : "low"}`}>{risk}</span>
      </header>

      {recommendation ? (
        <section className="decision-band" aria-labelledby="decision-heading">
          <div>
            <p className="section-kicker">Recommended operator action</p>
            <h3 id="decision-heading">{recommendation.label}</h3>
            <p>{recommendation.summary || "Review the extracted facts and evidence before taking action."}</p>
          </div>
          <dl className="decision-signals">
            <div><dt>Confidence</dt><dd>{Math.round((recommendation.confidence || 0) * 100)}%</dd></div>
            <div><dt>Human review</dt><dd>{recommendation.humanReviewRequired ? "Required" : "Not required"}</dd></div>
            <div><dt>Policy sources</dt><dd>{caseResult.evidence.length}</dd></div>
          </dl>
        </section>
      ) : (
        <section className="pending-case-band">
          <LoaderCircle className={latestJob?.status === "processing" ? "spin" : ""} size={21} aria-hidden="true" />
          <div>
            <h3>{humanize(detail.document.status)}</h3>
            <p>The recommendation and evidence will appear after processing completes.</p>
          </div>
        </section>
      )}

      {reasons.length > 0 ? (
        <section className="reason-strip" aria-label="Reasons requiring attention">
          <strong>Why attention is needed</strong>
          <div>{reasons.map((reason) => <span key={reason}>{reasonLabel(reason)}</span>)}</div>
        </section>
      ) : null}

      <div className="case-section-heading">
        <div>
          <p className="section-kicker">01 · Extracted facts</p>
          <h3>Case summary</h3>
        </div>
        {detail.document.status === "completed" ? (
          accessLink ? (
            <a className="icon-text-button" href={accessLink.url} target="_blank" rel="noreferrer">
              <ExternalLink size={17} aria-hidden="true" /> Open private document
            </a>
          ) : (
            <button className="icon-text-button" type="button" onClick={prepareAccess} disabled={accessBusy}>
              {accessBusy ? <LoaderCircle className="spin" size={17} aria-hidden="true" /> : <FileSearch size={17} aria-hidden="true" />}
              {accessBusy ? "Preparing link" : "Prepare document link"}
            </button>
          )
        ) : null}
      </div>

      {facts.length > 0 ? (
        <dl className="fact-grid">
          {facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl>
      ) : <p className="section-empty">Structured facts are not available yet.</p>}

      <div className="case-section-heading">
        <div>
          <p className="section-kicker">02 · Grounded support</p>
          <h3>Policy evidence</h3>
        </div>
      </div>

      {caseResult?.evidence?.length ? (
        <div className="evidence-list">
          {caseResult.evidence.map((item, index) => (
            <article className="evidence-item" key={`${item.source_id || "evidence"}-${index}`}>
              <div><span>Source {index + 1}</span><strong>{item.source_title || item.source_id || "Policy source"}</strong></div>
              <p>{item.excerpt || "No excerpt was stored for this source."}</p>
              <small>{item.relevance_reason || `Citation ${item.source_id || "not available"}`}</small>
            </article>
          ))}
        </div>
      ) : <p className="section-empty">No supporting policy evidence is available. Keep this case in human review.</p>}

      <details className="case-disclosure" open>
        <summary>Extracted source pages <span>{pages.length}</span></summary>
        <div className="page-list">
          {pages.length ? pages.map((page) => (
            <article className="page-item" key={page.page_number}>
              <header>
                <strong>Page {page.page_number}</strong>
                <span>{humanize(page.extraction_method)} extraction</span>
              </header>
              <p>{page.text || "No readable text was extracted from this page."}</p>
              {accessLink ? <a href={`${accessLink.url}#page=${page.page_number}`} target="_blank" rel="noreferrer">Open page <ExternalLink size={14} aria-hidden="true" /></a> : null}
            </article>
          )) : <p className="section-empty">No page text is available yet.</p>}
        </div>
      </details>

      <details className="case-disclosure">
        <summary>Technical workflow trace <span>{caseResult?.agent_tool_trace?.length || 0}</span></summary>
        <div className="trace-list">
          {(caseResult?.agent_tool_trace || []).map((trace, index) => (
            <div key={`${trace.tool_name || "step"}-${index}`}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><strong>{humanize(trace.tool_name)}</strong><p>{trace.output_summary || trace.purpose}</p></div>
            </div>
          ))}
          {!caseResult?.agent_tool_trace?.length ? <p className="section-empty">No technical trace is available yet.</p> : null}
        </div>
      </details>

      <div className="case-section-heading">
        <div>
          <p className="section-kicker">03 · Human control</p>
          <h3>Record review decision</h3>
        </div>
      </div>

      {caseResult?.processing_job_id ? (
        <form className="review-form" onSubmit={submitReview}>
          <fieldset>
            <legend>Choose an operator action</legend>
            <div className="review-actions">
              {REVIEW_ACTIONS.map((action) => (
                <label key={action.value} className={reviewAction === action.value ? "selected" : ""}>
                  <input type="radio" name="review-action" value={action.value} checked={reviewAction === action.value} onChange={() => setReviewAction(action.value)} />
                  {action.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="review-field">
            <span>Decision reason</span>
            <input value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} maxLength={500} required />
          </label>
          <label className="review-field">
            <span>Reviewer note <small>Optional</small></span>
            <textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} maxLength={5000} rows={3} placeholder="Add the next step or context for another reviewer." />
          </label>
          <button className="primary-button review-submit" type="submit" disabled={reviewBusy || !reviewAction || !reviewReason.trim()}>
            {reviewBusy ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <CheckCircle2 size={18} aria-hidden="true" />}
            {reviewBusy ? "Saving decision" : "Save review decision"}
          </button>
        </form>
      ) : <p className="section-empty">Review actions unlock after a completed processing result is available.</p>}

      {reviewNotice ? <div className={`workspace-notice notice-${reviewNotice.tone}`} role={reviewNotice.tone === "danger" ? "alert" : "status"}>{reviewNotice.message}</div> : null}

      {detail.reviews.length > 0 ? (
        <div className="review-history">
          <h4>Recorded decisions</h4>
          {detail.reviews.map((review) => (
            <article key={review.id}>
              <strong>{humanize(review.action)}</strong>
              <span>{formatGmt(review.created_at)}</span>
              <p>{review.reason}</p>
              {review.reviewer_note ? <small>{review.reviewer_note}</small> : null}
            </article>
          ))}
        </div>
      ) : null}

      <div className="case-section-heading">
        <div>
          <p className="section-kicker">04 · Append-only record</p>
          <h3>Audit history</h3>
        </div>
        <History size={21} aria-hidden="true" />
      </div>

      <ol className="audit-list">
        {auditEvents.map((event) => (
          <li key={event.id}>
            <span className="audit-marker" aria-hidden="true" />
            <div><strong>{AUDIT_LABELS[event.action] || humanize(event.action)}</strong><small>{formatGmt(event.timestamp)} · Request {event.request_id.slice(0, 8)}</small></div>
          </li>
        ))}
      </ol>
      {auditEvents.length === 0 ? <p className="section-empty">No audit events have been recorded for this case.</p> : null}
    </section>
  );
}
