import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

const configuredAuth = {
  configured: true,
  issuer: "https://issuer.example.com/pool",
  client_id: "browser-client",
  authorization_endpoint: "https://login.example.com/oauth2/authorize",
  token_endpoint: "https://login.example.com/oauth2/token",
  logout_endpoint: "https://login.example.com/logout",
  jwks_uri: "https://issuer.example.com/pool/.well-known/jwks.json",
  redirect_uri: "https://app.example.com/reviewer/callback",
  post_logout_redirect_uri: "https://app.example.com/reviewer/",
  scopes: ["openid", "invoiceflow/read"]
};

function response(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

function location(pathname = "/reviewer/") {
  return { pathname, assign: vi.fn() };
}

describe("reviewer app", () => {
  it("shows a safe unavailable state when browser auth is not configured", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({ configured: false }));

    render(<App fetchImpl={fetchImpl} browserLocation={location()} />);

    expect(await screen.findByText("The protected workspace is not connected here.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open public demo/i })).toHaveAttribute("href", "/ui");
  });

  it("starts the Cognito redirect from the signed-out state", async () => {
    const signinRedirect = vi.fn().mockResolvedValue(undefined);
    const manager = {
      getUser: vi.fn().mockResolvedValue(null),
      signinRedirect,
      events: {}
    };
    const fetchImpl = vi.fn().mockResolvedValue(response(configuredAuth));

    render(
      <App
        fetchImpl={fetchImpl}
        authFactory={() => manager}
        browserLocation={location()}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: /sign in securely/i }));

    await waitFor(() => expect(signinRedirect).toHaveBeenCalledOnce());
  });

  it("verifies tenant identity before showing the authenticated workspace", async () => {
    const manager = {
      getUser: vi.fn().mockResolvedValue({
        expired: false,
        access_token: "private-access-token",
        expires_at: 1893456000
      }),
      events: {}
    };
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(response(configuredAuth))
      .mockResolvedValueOnce(
        response({
          organization_id: "11111111-1111-4111-8111-111111111111",
          actor_id: "22222222-2222-4222-8222-222222222222"
        })
      );

    render(
      <App
        fetchImpl={fetchImpl}
        authFactory={() => manager}
        browserLocation={location()}
      />
    );

    expect(await screen.findByRole("heading", { name: "Access verified." })).toBeInTheDocument();
    expect(screen.getByTitle("11111111-1111-4111-8111-111111111111")).toHaveTextContent("11111111...1111");
    expect(fetchImpl.mock.calls[1][1].headers.Authorization).toBe("Bearer private-access-token");
  });

  it("completes the callback before loading protected identity", async () => {
    const manager = {
      signinRedirectCallback: vi.fn().mockResolvedValue({
        expired: false,
        access_token: "callback-token",
        expires_at: 1893456000
      }),
      events: {}
    };
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(response(configuredAuth))
      .mockResolvedValueOnce(
        response({
          organization_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          actor_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        })
      );
    const browserHistory = { replaceState: vi.fn() };

    render(
      <App
        fetchImpl={fetchImpl}
        authFactory={() => manager}
        browserLocation={location("/reviewer/callback")}
        browserHistory={browserHistory}
      />
    );

    expect(await screen.findByRole("heading", { name: "Access verified." })).toBeInTheDocument();
    expect(manager.signinRedirectCallback).toHaveBeenCalledOnce();
    expect(browserHistory.replaceState).toHaveBeenCalledWith({}, document.title, "/reviewer/");
  });
});
