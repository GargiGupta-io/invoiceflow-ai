export class ReviewerApiError extends Error {
  constructor(message, status, code = "request_failed") {
    super(message);
    this.name = "ReviewerApiError";
    this.status = status;
    this.code = code;
  }
}

export async function getTenantIdentity(accessToken, fetchImpl = fetch) {
  const response = await fetchImpl("/v2/me", {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`
    },
    cache: "no-store"
  });

  if (!response.ok) {
    let detail = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = null;
    }
    const message = detail?.message || "The protected reviewer workspace could not be opened.";
    const code = detail?.code || "request_failed";
    throw new ReviewerApiError(message, response.status, code);
  }

  return response.json();
}
