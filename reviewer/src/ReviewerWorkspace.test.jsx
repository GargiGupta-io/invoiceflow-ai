import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReviewerWorkspace from "./ReviewerWorkspace.jsx";

function response(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

function document(overrides = {}) {
  return {
    id: "2fb87fb2-9ab0-4b69-8810-88bbbe5a1107",
    original_filename: "northstar-invoice.pdf",
    content_type: "application/pdf",
    size_bytes: 24576,
    page_count: 2,
    status: "completed",
    created_at: "2026-07-19T10:30:00Z",
    ...overrides
  };
}

describe("reviewer workspace", () => {
  it("renders persistent tenant history with readable processing states", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      response({
        items: [
          document(),
          document({ id: "8b6343bf-7735-4494-807c-2d8f129cb625", original_filename: "receipt.jpg", content_type: "image/jpeg", status: "processing" })
        ],
        count: 2
      })
    );

    const view = render(<ReviewerWorkspace accessToken="tenant-token" fetchImpl={fetchImpl} />);

    expect(await screen.findByText("northstar-invoice.pdf")).toBeInTheDocument();
    expect(screen.getAllByText("Complete").length).toBeGreaterThan(0);
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getAllByText(/2 pages/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/GMT$/).length).toBeGreaterThan(0);
    view.unmount();
  });

  it("uploads a document and dispatches it with one operator action", async () => {
    const uploaded = document({ status: "quarantined" });
    const queued = { ...uploaded, status: "queued" };
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [], count: 0 }))
      .mockResolvedValueOnce(response({ document: uploaded, request_id: "request-1" }, 201))
      .mockResolvedValueOnce(response({ processing_job: { id: "job-1", status: "queued" } }, 202))
      .mockResolvedValue(response({ items: [queued], count: 1 }));

    const view = render(<ReviewerWorkspace accessToken="tenant-token" fetchImpl={fetchImpl} />);
    await screen.findByText("No tenant documents yet");

    const file = new File(["invoice"], "northstar-invoice.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/choose file/i), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /upload and process/i }));

    expect(await screen.findByText(/queued for processing/i)).toBeInTheDocument();
    const uploadOptions = fetchImpl.mock.calls[1][1];
    const dispatchOptions = fetchImpl.mock.calls[2][1];
    expect(uploadOptions.body.get("file")).toBe(file);
    expect(dispatchOptions.headers.get("Idempotency-Key")).toBe(`reviewer-${uploaded.id}`);
    view.unmount();
  });

  it("lets a reviewer start a quarantined document manually", async () => {
    const quarantined = document({ status: "quarantined" });
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [quarantined], count: 1 }))
      .mockResolvedValueOnce(response({ processing_job: { id: "job-1", status: "queued" } }, 202))
      .mockResolvedValue(response({ items: [{ ...quarantined, status: "queued" }], count: 1 }));

    const view = render(<ReviewerWorkspace accessToken="tenant-token" fetchImpl={fetchImpl} />);
    fireEvent.click(await screen.findByRole("button", { name: /start processing/i }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(3));
    expect(fetchImpl.mock.calls[1][0]).toContain("/processing-jobs");
    view.unmount();
  });

  it("reuses the same queue request after a temporary dispatch failure", async () => {
    const quarantined = document({ status: "quarantined" });
    const queued = { ...quarantined, status: "queued" };
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [quarantined], count: 1 }))
      .mockResolvedValueOnce(
        response({ detail: { code: "queue_unavailable", message: "The queue is temporarily unavailable." } }, 503)
      )
      .mockResolvedValueOnce(response({ items: [queued], count: 1 }))
      .mockResolvedValueOnce(response({ processing_job: { id: "job-1", status: "queued" } }, 202))
      .mockResolvedValue(response({ items: [queued], count: 1 }));

    const view = render(<ReviewerWorkspace accessToken="tenant-token" fetchImpl={fetchImpl} />);
    fireEvent.click(await screen.findByRole("button", { name: /start processing/i }));

    fireEvent.click(await screen.findByRole("button", { name: /retry queue/i }));
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(5));

    const firstKey = fetchImpl.mock.calls[1][1].headers.get("Idempotency-Key");
    const retryKey = fetchImpl.mock.calls[3][1].headers.get("Idempotency-Key");
    expect(retryKey).toBe(firstKey);
    view.unmount();
  });

  it("returns control to the login shell when the token expires", async () => {
    const onSessionInvalid = vi.fn();
    const fetchImpl = vi.fn().mockResolvedValue(
      response({ detail: { code: "invalid_token", message: "The access token is no longer valid." } }, 401)
    );

    render(
      <ReviewerWorkspace
        accessToken="expired-token"
        fetchImpl={fetchImpl}
        onSessionInvalid={onSessionInvalid}
      />
    );

    await waitFor(() => expect(onSessionInvalid).toHaveBeenCalledOnce());
  });
});
