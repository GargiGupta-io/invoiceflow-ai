export class ReviewerApiError extends Error {
  constructor(message, status, code = "request_failed") {
    super(message);
    this.name = "ReviewerApiError";
    this.status = status;
    this.code = code;
  }
}

async function responseDetail(response, fallbackMessage) {
  try {
    const payload = await response.json();
    const detail = payload?.detail;
    if (typeof detail === "string") {
      return { message: detail, code: "request_failed" };
    }
    return {
      message: detail?.message || fallbackMessage,
      code: detail?.code || "request_failed"
    };
  } catch {
    return { message: fallbackMessage, code: "request_failed" };
  }
}

async function reviewerRequest(path, accessToken, options = {}, fetchImpl = fetch) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetchImpl(path, {
    ...options,
    headers,
    cache: "no-store"
  });

  if (!response.ok) {
    const detail = await responseDetail(
      response,
      options.fallbackMessage || "The protected reviewer request could not be completed."
    );
    throw new ReviewerApiError(detail.message, response.status, detail.code);
  }

  return response.json();
}

export async function getTenantIdentity(accessToken, fetchImpl = fetch) {
  return reviewerRequest(
    "/v2/me",
    accessToken,
    { fallbackMessage: "The protected reviewer workspace could not be opened." },
    fetchImpl
  );
}

export async function listTenantDocuments(accessToken, fetchImpl = fetch) {
  return reviewerRequest(
    "/v2/documents?limit=50",
    accessToken,
    { fallbackMessage: "Document history could not be loaded." },
    fetchImpl
  );
}

export async function uploadTenantDocument(accessToken, file, fetchImpl = fetch) {
  const body = new FormData();
  body.append("file", file);
  return reviewerRequest(
    "/v2/documents",
    accessToken,
    {
      method: "POST",
      body,
      fallbackMessage: "The document could not be uploaded."
    },
    fetchImpl
  );
}

export async function dispatchDocumentProcessing(
  accessToken,
  documentId,
  fetchImpl = fetch
) {
  return reviewerRequest(
    `/v2/documents/${documentId}/processing-jobs`,
    accessToken,
    {
      method: "POST",
      headers: { "Idempotency-Key": `reviewer-${documentId}` },
      fallbackMessage: "Document processing could not be started."
    },
    fetchImpl
  );
}

export async function getTenantDocument(accessToken, documentId, fetchImpl = fetch) {
  return reviewerRequest(
    `/v2/documents/${documentId}`,
    accessToken,
    { fallbackMessage: "The case detail could not be loaded." },
    fetchImpl
  );
}

export async function listDocumentPages(accessToken, documentId, fetchImpl = fetch) {
  return reviewerRequest(
    `/v2/documents/${documentId}/pages`,
    accessToken,
    { fallbackMessage: "Extracted document pages could not be loaded." },
    fetchImpl
  );
}

export async function listDocumentAudit(accessToken, documentId, fetchImpl = fetch) {
  return reviewerRequest(
    `/v2/documents/${documentId}/audit`,
    accessToken,
    { fallbackMessage: "Audit history could not be loaded." },
    fetchImpl
  );
}

export async function requestDocumentAccess(accessToken, documentId, fetchImpl = fetch) {
  return reviewerRequest(
    `/v2/documents/${documentId}/access`,
    accessToken,
    {
      method: "POST",
      fallbackMessage: "Private document access could not be prepared."
    },
    fetchImpl
  );
}

export async function createReviewDecision(
  accessToken,
  documentId,
  review,
  fetchImpl = fetch
) {
  return reviewerRequest(
    `/v2/documents/${documentId}/reviews`,
    accessToken,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(review),
      fallbackMessage: "The review decision could not be saved."
    },
    fetchImpl
  );
}
