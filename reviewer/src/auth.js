import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const CONFIG_PATH = "/v2/auth/config";

export class AuthConfigurationError extends Error {
  constructor(message) {
    super(message);
    this.name = "AuthConfigurationError";
  }
}

export async function loadAuthConfig(fetchImpl = fetch) {
  const response = await fetchImpl(CONFIG_PATH, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new AuthConfigurationError("Reviewer login settings could not be loaded.");
  }
  return response.json();
}

export function createAuthManager(config, storage = window.sessionStorage) {
  if (!config.configured) {
    throw new AuthConfigurationError("Reviewer login is not configured.");
  }

  return new UserManager({
    authority: config.issuer,
    client_id: config.client_id,
    redirect_uri: config.redirect_uri,
    response_type: "code",
    scope: config.scopes.join(" "),
    post_logout_redirect_uri: config.post_logout_redirect_uri,
    monitorSession: false,
    automaticSilentRenew: false,
    loadUserInfo: false,
    stateStore: new WebStorageStateStore({ store: storage }),
    userStore: new WebStorageStateStore({ store: storage }),
    metadata: {
      issuer: config.issuer,
      authorization_endpoint: config.authorization_endpoint,
      token_endpoint: config.token_endpoint,
      end_session_endpoint: config.logout_endpoint,
      jwks_uri: config.jwks_uri
    }
  });
}

export async function signOut(manager, config, location = window.location) {
  await manager.removeUser();
  const logoutUrl = new URL(config.logout_endpoint);
  logoutUrl.searchParams.set("client_id", config.client_id);
  logoutUrl.searchParams.set("logout_uri", config.post_logout_redirect_uri);
  location.assign(logoutUrl.toString());
}
