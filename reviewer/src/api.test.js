import { describe, expect, it, vi } from "vitest";

import {
  ReviewerApiError,
  dispatchDocumentProcessing,
  listTenantDocuments,
  uploadTenantDocument
} from "./api.js";

function response(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

describe("reviewer api", () => {
  it("loads tenant history without browser caching", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({ items: [], count: 0 }));

    await listTenantDocuments("tenant-token", fetchImpl);

    const [path, options] = fetchImpl.mock.calls[0];
    expect(path).toBe("/v2/documents?limit=50");
    expect(options.cache).toBe("no-store");
    expect(options.headers.get("Authorization")).toBe("Bearer tenant-token");
  });

  it("uploads multipart data without overriding its content type", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({ document: { id: "doc-1" } }, 201));
    const file = new File(["invoice"], "invoice.pdf", { type: "application/pdf" });

    await uploadTenantDocument("tenant-token", file, fetchImpl);

    const [, options] = fetchImpl.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("file")).toBe(file);
    expect(options.headers.has("Content-Type")).toBe(false);
  });

  it("uses a reproducible idempotency key for processing dispatch", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({ processing_job: { id: "job-1" } }, 202));

    await dispatchDocumentProcessing("tenant-token", "2fb87fb2-9ab0-4b69-8810-88bbbe5a1107", fetchImpl);

    const [path, options] = fetchImpl.mock.calls[0];
    expect(path).toContain("/processing-jobs");
    expect(options.headers.get("Idempotency-Key")).toBe(
      "reviewer-2fb87fb2-9ab0-4b69-8810-88bbbe5a1107"
    );
  });

  it("preserves structured API errors for the workspace", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      response({ detail: { code: "file_too_large", message: "The file exceeds the upload limit." } }, 413)
    );

    await expect(listTenantDocuments("tenant-token", fetchImpl)).rejects.toMatchObject({
      name: "ReviewerApiError",
      status: 413,
      code: "file_too_large",
      message: "The file exceeds the upload limit."
    });
    await expect(listTenantDocuments("tenant-token", fetchImpl)).rejects.toBeInstanceOf(ReviewerApiError);
  });
});
