import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileImage,
  FileText,
  LoaderCircle,
  Play,
  RefreshCw,
  UploadCloud
} from "lucide-react";

import CaseDetail from "./CaseDetail.jsx";
import {
  ReviewerApiError,
  dispatchDocumentProcessing,
  listTenantDocuments,
  uploadTenantDocument
} from "./api.js";

const ACTIVE_STATUSES = new Set(["queued", "processing"]);
const NOOP = () => {};

const STATUS_COPY = {
  quarantined: { label: "Ready to process", tone: "neutral", step: "Upload checked" },
  validated: { label: "Validated", tone: "neutral", step: "File validated" },
  queued: { label: "Queued", tone: "pending", step: "Waiting for worker" },
  processing: { label: "Processing", tone: "pending", step: "Extracting document" },
  completed: { label: "Complete", tone: "success", step: "Ready for review" },
  failed: { label: "Failed", tone: "danger", step: "Needs attention" }
};

function statusCopy(status) {
  return STATUS_COPY[status] || { label: "Unknown", tone: "neutral", step: "Status unavailable" };
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "Unknown size";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

function formatPageCount(pageCount) {
  if (!pageCount) return "Page count pending";
  return `${pageCount} ${pageCount === 1 ? "page" : "pages"}`;
}

function documentIcon(contentType) {
  return contentType?.startsWith("image/") ? FileImage : FileText;
}

function replaceDocument(items, nextDocument) {
  const remaining = items.filter((item) => item.id !== nextDocument.id);
  return [nextDocument, ...remaining];
}

function UploadProgress({ stage }) {
  if (stage === "idle") return null;
  const queueing = stage === "queueing";
  return (
    <div className="upload-progress" role="status">
      <LoaderCircle className="spin" size={17} aria-hidden="true" />
      <span>{queueing ? "Saving the processing request..." : "Validating and storing the document..."}</span>
    </div>
  );
}

function StatusBadge({ status }) {
  const copy = statusCopy(status);
  return <span className={`document-status status-${copy.tone}`}>{copy.label}</span>;
}

function DocumentRow({ document, actionBusy, canRetryQueue, onOpen, onProcess }) {
  const copy = statusCopy(document.status);
  const Icon = documentIcon(document.content_type);
  const canProcess = document.status === "quarantined" || canRetryQueue;

  return (
    <article className="document-row">
      <div className="document-name-cell">
        <span className="document-icon"><Icon size={20} aria-hidden="true" /></span>
        <div>
          <h3>{document.original_filename}</h3>
          <p>{formatBytes(document.size_bytes)} · {formatPageCount(document.page_count)}</p>
        </div>
      </div>
      <div className="document-stage-cell">
        <StatusBadge status={document.status} />
        <span>{copy.step}</span>
      </div>
      <div className="document-time-cell">
        <span>Uploaded</span>
        <strong>{formatGmt(document.created_at)}</strong>
      </div>
      <div className="document-action-cell">
        {canProcess ? (
          <button
            className="compact-button"
            type="button"
            onClick={() => onProcess(document)}
            disabled={actionBusy}
          >
            {actionBusy ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
            {actionBusy ? "Starting" : canRetryQueue ? "Retry queue" : "Start processing"}
          </button>
        ) : (
          <button className="compact-button" type="button" onClick={() => onOpen(document.id)}>
            Open case
          </button>
        )}
      </div>
    </article>
  );
}

export default function ReviewerWorkspace({
  accessToken,
  fetchImpl = fetch,
  onSessionInvalid = NOOP
}) {
  const [documents, setDocuments] = useState([]);
  const [historyState, setHistoryState] = useState("loading");
  const [historyError, setHistoryError] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStage, setUploadStage] = useState("idle");
  const [actionDocumentId, setActionDocumentId] = useState(null);
  const [queueRetryIds, setQueueRetryIds] = useState(() => new Set());
  const [notice, setNotice] = useState(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const fileInputRef = useRef(null);

  const handleApiError = useCallback((error, fallbackMessage) => {
    if (error instanceof ReviewerApiError && error.status === 401) {
      onSessionInvalid();
      return "Your reviewer session expired. Sign in again.";
    }
    return error instanceof Error ? error.message : fallbackMessage;
  }, [onSessionInvalid]);

  const refreshDocuments = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setHistoryState("loading");
      setHistoryError("");
    }
    try {
      const payload = await listTenantDocuments(accessToken, fetchImpl);
      setDocuments(payload.items || []);
      setHistoryState("ready");
    } catch (error) {
      const message = handleApiError(error, "Document history could not be loaded.");
      if (!silent) {
        setHistoryError(message);
        setHistoryState("error");
      }
    }
  }, [accessToken, fetchImpl, handleApiError]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const hasActiveProcessing = useMemo(
    () => documents.some((document) => ACTIVE_STATUSES.has(document.status)),
    [documents]
  );

  useEffect(() => {
    if (!hasActiveProcessing) return undefined;
    const poll = window.setInterval(() => refreshDocuments({ silent: true }), 4000);
    return () => window.clearInterval(poll);
  }, [hasActiveProcessing, refreshDocuments]);

  const counts = useMemo(() => ({
    total: documents.length,
    active: documents.filter((document) => ACTIVE_STATUSES.has(document.status)).length,
    completed: documents.filter((document) => document.status === "completed").length
  }), [documents]);

  async function startProcessing(document, { fromUpload = false } = {}) {
    setActionDocumentId(document.id);
    if (fromUpload) setUploadStage("queueing");
    try {
      await dispatchDocumentProcessing(accessToken, document.id, fetchImpl);
      setQueueRetryIds((ids) => {
        const nextIds = new Set(ids);
        nextIds.delete(document.id);
        return nextIds;
      });
      setDocuments((items) => replaceDocument(items, { ...document, status: "queued" }));
      setNotice({ tone: "success", message: `${document.original_filename} is queued for processing.` });
      await refreshDocuments({ silent: true });
      return true;
    } catch (error) {
      setQueueRetryIds((ids) => new Set(ids).add(document.id));
      setNotice({
        tone: "warning",
        message: `${document.original_filename} was saved, but processing could not start. ${handleApiError(error, "Try again.")}`
      });
      await refreshDocuments({ silent: true });
      return false;
    } finally {
      setActionDocumentId(null);
      if (fromUpload) setUploadStage("idle");
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!selectedFile || uploadStage !== "idle") return;

    setNotice(null);
    setUploadStage("uploading");
    try {
      const receipt = await uploadTenantDocument(accessToken, selectedFile, fetchImpl);
      setDocuments((items) => replaceDocument(items, receipt.document));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await startProcessing(receipt.document, { fromUpload: true });
    } catch (error) {
      setNotice({
        tone: "danger",
        message: handleApiError(error, "The document could not be uploaded.")
      });
      setUploadStage("idle");
    }
  }

  if (selectedDocumentId) {
    return (
      <CaseDetail
        accessToken={accessToken}
        documentId={selectedDocumentId}
        fetchImpl={fetchImpl}
        onBack={() => setSelectedDocumentId(null)}
        onSessionInvalid={onSessionInvalid}
      />
    );
  }

  return (
    <div className="document-workspace">
      <section className="workspace-intro">
        <div>
          <p className="eyebrow">Tenant document pipeline</p>
          <h2>Upload and track finance cases.</h2>
          <p>Each accepted document is stored privately, queued once, and kept in this organization&apos;s history.</p>
        </div>
        <button
          className="icon-text-button"
          type="button"
          onClick={() => refreshDocuments()}
          disabled={historyState === "loading"}
        >
          <RefreshCw className={historyState === "loading" ? "spin" : ""} size={17} aria-hidden="true" />
          Refresh
        </button>
      </section>

      <form className="document-upload" onSubmit={handleUpload}>
        <div className="upload-heading">
          <UploadCloud size={22} aria-hidden="true" />
          <div>
            <h3>New document</h3>
            <p>PDF, PNG, or JPEG. The server verifies the type, signature, parser, size, and page limit.</p>
          </div>
        </div>
        <div className="upload-controls">
          <label className="file-control">
            <span>{selectedFile ? "Change file" : "Choose file"}</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              disabled={uploadStage !== "idle"}
            />
          </label>
          <div className="selected-file" aria-live="polite">
            {selectedFile ? (
              <>
                <strong>{selectedFile.name}</strong>
                <span>{formatBytes(selectedFile.size)}</span>
              </>
            ) : (
              <span>No document selected</span>
            )}
          </div>
          <button className="primary-button upload-button" type="submit" disabled={!selectedFile || uploadStage !== "idle"}>
            {uploadStage !== "idle" ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <UploadCloud size={18} aria-hidden="true" />}
            {uploadStage === "uploading" ? "Uploading" : uploadStage === "queueing" ? "Queueing" : "Upload and process"}
          </button>
        </div>
        <UploadProgress stage={uploadStage} />
      </form>

      {notice ? (
        <div className={`workspace-notice notice-${notice.tone}`} role={notice.tone === "danger" ? "alert" : "status"}>
          {notice.tone === "success" ? <CheckCircle2 size={19} aria-hidden="true" /> : <AlertTriangle size={19} aria-hidden="true" />}
          <span>{notice.message}</span>
        </div>
      ) : null}

      <section className="history-section" aria-labelledby="document-history-heading">
        <div className="history-heading">
          <div>
            <p className="eyebrow">Saved workspace</p>
            <h2 id="document-history-heading">Document history</h2>
          </div>
          <div className="history-counts" aria-label="Document totals">
            <span><strong>{counts.total}</strong> Cases</span>
            <span><strong>{counts.active}</strong> In progress</span>
            <span><strong>{counts.completed}</strong> Complete</span>
          </div>
        </div>

        {historyState === "loading" && documents.length === 0 ? (
          <div className="history-message" role="status">
            <LoaderCircle className="spin" size={21} aria-hidden="true" /> Loading tenant documents...
          </div>
        ) : null}

        {historyState === "error" ? (
          <div className="history-message history-error" role="alert">
            <AlertTriangle size={21} aria-hidden="true" />
            <span>{historyError}</span>
            <button type="button" onClick={() => refreshDocuments()}>Try again</button>
          </div>
        ) : null}

        {historyState === "ready" && documents.length === 0 ? (
          <div className="history-empty">
            <Clock3 size={24} aria-hidden="true" />
            <h3>No tenant documents yet</h3>
            <p>Choose a supported file above to create the first persistent case.</p>
          </div>
        ) : null}

        {documents.length > 0 ? (
          <div className="document-list">
            <div className="document-list-header" aria-hidden="true">
              <span>Document</span><span>Pipeline state</span><span>Created</span><span>Action</span>
            </div>
            {documents.map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                actionBusy={actionDocumentId === document.id}
                canRetryQueue={queueRetryIds.has(document.id)}
                onOpen={setSelectedDocumentId}
                onProcess={startProcessing}
              />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
