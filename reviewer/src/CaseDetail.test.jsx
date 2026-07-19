import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CaseDetail from "./CaseDetail.jsx";

function response(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

const documentId = "2fb87fb2-9ab0-4b69-8810-88bbbe5a1107";
const jobId = "6adbf187-b7b0-4a6c-bc2c-9ff23fb72af1";

function caseDetail() {
  return {
    document: {
      id: documentId,
      original_filename: "northstar-invoice.pdf",
      content_type: "application/pdf",
      size_bytes: 24576,
      page_count: 2,
      status: "completed",
      created_at: "2026-07-19T10:30:00Z"
    },
    processing_jobs: [{ id: jobId, status: "completed", completed_at: "2026-07-19T10:31:00Z" }],
    reviews: [],
    case_result: {
      processing_job_id: jobId,
      workflow_result: {
        workflow_type: "accounts_payable",
        extraction: {
          vendor_name: "Northstar Supplies",
          invoice_number: "NS-2048",
          amount: 7800,
          currency: "USD",
          due_date: "2026-08-01",
          po_number: null
        },
        ap_decision: {
          recommendation: "missing_info",
          reviewer_summary: "A purchase order is required before payment can continue.",
          confidence: 0.78,
          human_review_required: true
        }
      },
      human_review: {
        required: true,
        blocking: true,
        reason_codes: ["po_required_missing"],
        reviewer_prompt: "Request the missing purchase order."
      },
      evidence: [{
        source_id: "AP-APPROVAL-001",
        source_title: "AP Approval Policy",
        excerpt: "Invoices above the threshold require a purchase order.",
        relevance_reason: "Defines the purchase order requirement."
      }],
      agent_tool_trace: [{ tool_name: "search_finance_policy", output_summary: "1 policy source retrieved" }],
      route: {},
      policy_assessment: {},
      stage_latencies_ms: {}
    }
  };
}

function fetchRouter() {
  return vi.fn(async (path, options = {}) => {
    if (path.endsWith("/pages")) {
      return response({
        items: [{ page_number: 1, text: "Invoice NS-2048 with no PO number.", extraction_method: "native", warnings: [] }],
        count: 1
      });
    }
    if (path.endsWith("/audit")) {
      return response([{
        id: "audit-1",
        action: "document.processing_completed",
        timestamp: "2026-07-19T10:31:00Z",
        request_id: "request-12345678",
        safe_metadata: {}
      }]);
    }
    if (path.endsWith("/access") && options.method === "POST") {
      return response({ url: "https://private.example.test/invoice", expires_in_seconds: 300 });
    }
    if (path.endsWith("/reviews") && options.method === "POST") {
      return response({ id: "review-1", action: "returned_for_info" }, 201);
    }
    if (path === `/v2/documents/${documentId}`) return response(caseDetail());
    throw new Error(`Unexpected request: ${path}`);
  });
}

describe("case detail", () => {
  it("shows a decision-first case with evidence, source pages, and audit history", async () => {
    render(<CaseDetail accessToken="tenant-token" documentId={documentId} fetchImpl={fetchRouter()} onBack={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Request missing info" })).toBeInTheDocument();
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("Northstar Supplies")).toBeInTheDocument();
    expect(screen.getByText("AP Approval Policy")).toBeInTheDocument();
    expect(screen.getByText("Invoice NS-2048 with no PO number.")).toBeInTheDocument();
    expect(screen.getByText("Extraction completed")).toBeInTheDocument();
    expect(screen.getByText("Missing purchase order")).toBeInTheDocument();
  });

  it("prepares a short-lived private document link on demand", async () => {
    const fetchImpl = fetchRouter();
    render(<CaseDetail accessToken="tenant-token" documentId={documentId} fetchImpl={fetchImpl} onBack={vi.fn()} />);
    await screen.findByRole("heading", { name: "Request missing info" });

    fireEvent.click(screen.getByRole("button", { name: /prepare document link/i }));

    const link = await screen.findByRole("link", { name: /open private document/i });
    expect(link).toHaveAttribute("href", "https://private.example.test/invoice");
    expect(fetchImpl.mock.calls.some(([path, options]) => path.endsWith("/access") && options.method === "POST")).toBe(true);
  });

  it("records the selected human decision and refreshes the audit view", async () => {
    const fetchImpl = fetchRouter();
    render(<CaseDetail accessToken="tenant-token" documentId={documentId} fetchImpl={fetchImpl} onBack={vi.fn()} />);
    await screen.findByRole("heading", { name: "Request missing info" });

    fireEvent.click(await screen.findByRole("button", { name: /save review decision/i }));

    expect(await screen.findByText(/review decision saved/i)).toBeInTheDocument();
    const reviewCall = fetchImpl.mock.calls.find(([path, options]) => path.endsWith("/reviews") && options.method === "POST");
    expect(JSON.parse(reviewCall[1].body)).toMatchObject({
      processing_job_id: jobId,
      action: "returned_for_info",
      reason: "A purchase order is required before payment can continue."
    });
    await waitFor(() => expect(fetchImpl.mock.calls.filter(([path]) => path.endsWith("/audit"))).toHaveLength(2));
  });

  it("returns to document history without changing the tenant session", async () => {
    const onBack = vi.fn();
    render(<CaseDetail accessToken="tenant-token" documentId={documentId} fetchImpl={fetchRouter()} onBack={onBack} />);
    await screen.findByRole("heading", { name: "Request missing info" });

    fireEvent.click(screen.getByRole("button", { name: /back to history/i }));

    expect(onBack).toHaveBeenCalledOnce();
  });
});
