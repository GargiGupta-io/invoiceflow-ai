import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Building2,
  Check,
  Clock3,
  FileCheck2,
  LogIn,
  LogOut,
  RefreshCw,
  ShieldCheck,
  UserRoundCheck
} from "lucide-react";

import { getTenantIdentity } from "./api.js";
import { createAuthManager, loadAuthConfig, signOut } from "./auth.js";

const INITIAL_STATE = { phase: "loading", message: "Checking reviewer access..." };

function formatIdentifier(value) {
  if (!value || value.length < 13) {
    return value || "Unavailable";
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function formatExpiry(expiresAt) {
  if (!expiresAt) {
    return "Session active";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(new Date(expiresAt * 1000));
}

function Brand() {
  return (
    <a className="brand" href="/reviewer/" aria-label="InvoiceFlow AI reviewer workspace">
      <span className="brand-mark" aria-hidden="true">iflow</span>
      <span>
        <strong>InvoiceFlow AI</strong>
        <small>Reviewer workspace</small>
      </span>
    </a>
  );
}

function Header({ authenticated, onSignOut }) {
  return (
    <header className="reviewer-header">
      <Brand />
      <div className="header-status">
        <span className="environment-label">Version 2</span>
        <span className="ready-label"><span aria-hidden="true" />Protected</span>
        {authenticated ? (
          <button className="icon-button" type="button" onClick={onSignOut} title="Sign out">
            <LogOut size={18} aria-hidden="true" />
            <span className="sr-only">Sign out</span>
          </button>
        ) : null}
      </div>
    </header>
  );
}

function LoadingView({ message }) {
  return (
    <main className="centered-state" aria-live="polite">
      <RefreshCw className="spin" size={26} aria-hidden="true" />
      <p>{message}</p>
    </main>
  );
}

function UnavailableView({ error, onRetry }) {
  return (
    <main className="reviewer-main">
      <section className="entry-band">
        <p className="eyebrow">Reviewer access unavailable</p>
        <h1>The protected workspace is not connected here.</h1>
        <p className="lede">{error || "Cognito browser login has not been configured for this environment."}</p>
        <div className="command-row">
          <button className="secondary-button" type="button" onClick={onRetry}>
            <RefreshCw size={18} aria-hidden="true" /> Retry
          </button>
          <a className="text-link" href="/ui">Open public demo <ArrowRight size={17} aria-hidden="true" /></a>
        </div>
      </section>
    </main>
  );
}

function SignedOutView({ onSignIn, busy }) {
  return (
    <main className="reviewer-main">
      <section className="entry-band">
        <p className="eyebrow">Finance review desk</p>
        <h1>Open your organization&apos;s protected case workspace.</h1>
        <p className="lede">
          Sign in to reach tenant-owned documents, evidence, decisions, and audit history.
        </p>
        <button className="primary-button" type="button" onClick={onSignIn} disabled={busy}>
          <LogIn size={19} aria-hidden="true" />
          {busy ? "Opening secure sign-in..." : "Sign in securely"}
        </button>
      </section>

      <section className="trust-rail" aria-label="Reviewer workspace controls">
        <div>
          <Building2 size={21} aria-hidden="true" />
          <strong>Tenant isolated</strong>
          <span>Organization ownership is enforced by the API and database.</span>
        </div>
        <div>
          <FileCheck2 size={21} aria-hidden="true" />
          <strong>Evidence linked</strong>
          <span>Document pages and policy support stay attached to each case.</span>
        </div>
        <div>
          <UserRoundCheck size={21} aria-hidden="true" />
          <strong>Human controlled</strong>
          <span>Review actions are attributed and preserved in the audit history.</span>
        </div>
      </section>
    </main>
  );
}

function AuthenticatedView({ identity, user, onSignOut }) {
  return (
    <main className="reviewer-main authenticated-main">
      <section className="workspace-heading">
        <div>
          <p className="eyebrow">Protected reviewer workspace</p>
          <h1>Access verified.</h1>
          <p className="lede">Your signed session is connected to one InvoiceFlow organization.</p>
        </div>
        <button className="secondary-button" type="button" onClick={onSignOut}>
          <LogOut size={18} aria-hidden="true" /> Sign out
        </button>
      </section>

      <section className="identity-strip" aria-label="Authenticated workspace identity">
        <div>
          <span className="fact-label"><Building2 size={17} aria-hidden="true" /> Organization</span>
          <strong title={identity.organization_id}>{formatIdentifier(identity.organization_id)}</strong>
        </div>
        <div>
          <span className="fact-label"><ShieldCheck size={17} aria-hidden="true" /> Reviewer</span>
          <strong title={identity.actor_id}>{formatIdentifier(identity.actor_id)}</strong>
        </div>
        <div>
          <span className="fact-label"><Clock3 size={17} aria-hidden="true" /> Session</span>
          <strong>{formatExpiry(user.expires_at)}</strong>
        </div>
      </section>

      <section className="workspace-empty" aria-live="polite">
        <span className="success-icon"><Check size={24} aria-hidden="true" /></span>
        <div>
          <h2>Identity and organization checks passed</h2>
          <p>The reviewer can now request tenant-scoped workspace data from protected Version 2 APIs.</p>
        </div>
      </section>
    </main>
  );
}

export default function App({
  fetchImpl = fetch,
  authFactory = createAuthManager,
  browserLocation = window.location,
  browserHistory = window.history
}) {
  const [state, setState] = useState(INITIAL_STATE);
  const [retryKey, setRetryKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const managerRef = useRef(null);
  const configRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let removeExpiryListener = null;

    async function initialize() {
      setState(INITIAL_STATE);
      try {
        const config = await loadAuthConfig(fetchImpl);
        if (cancelled) return;
        if (!config.configured) {
          setState({ phase: "unavailable", message: "Cognito browser login is not configured for this environment." });
          return;
        }

        const manager = authFactory(config);
        managerRef.current = manager;
        configRef.current = config;

        const expireHandler = () => {
          setState({ phase: "signed-out", message: "Your reviewer session expired. Sign in again." });
        };
        manager.events?.addAccessTokenExpired?.(expireHandler);
        removeExpiryListener = () => manager.events?.removeAccessTokenExpired?.(expireHandler);

        let user;
        if (browserLocation.pathname.endsWith("/reviewer/callback")) {
          setState({ phase: "loading", message: "Completing secure sign-in..." });
          user = await manager.signinRedirectCallback();
          browserHistory.replaceState({}, document.title, "/reviewer/");
        } else {
          user = await manager.getUser();
        }

        if (cancelled) return;
        if (!user || user.expired || !user.access_token) {
          setState({ phase: "signed-out", message: null });
          return;
        }

        const identity = await getTenantIdentity(user.access_token, fetchImpl);
        if (!cancelled) {
          setState({ phase: "authenticated", identity, user });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            phase: "unavailable",
            message: error instanceof Error ? error.message : "Reviewer access could not be opened."
          });
        }
      }
    }

    initialize();
    return () => {
      cancelled = true;
      removeExpiryListener?.();
    };
  }, [authFactory, browserHistory, browserLocation.pathname, fetchImpl, retryKey]);

  async function handleSignIn() {
    if (!managerRef.current || busy) return;
    setBusy(true);
    try {
      await managerRef.current.signinRedirect();
    } catch (error) {
      setBusy(false);
      setState({ phase: "unavailable", message: error instanceof Error ? error.message : "Secure sign-in could not start." });
    }
  }

  async function handleSignOut() {
    if (!managerRef.current || !configRef.current) return;
    setBusy(true);
    try {
      await signOut(managerRef.current, configRef.current, browserLocation);
    } catch (error) {
      setBusy(false);
      setState({ phase: "unavailable", message: error instanceof Error ? error.message : "Sign out could not be completed." });
    }
  }

  const authenticated = state.phase === "authenticated";

  return (
    <div className="reviewer-app">
      <div className="dot-field" aria-hidden="true" />
      <Header authenticated={authenticated} onSignOut={handleSignOut} />
      {state.phase === "loading" ? <LoadingView message={state.message} /> : null}
      {state.phase === "unavailable" ? (
        <UnavailableView error={state.message} onRetry={() => setRetryKey((value) => value + 1)} />
      ) : null}
      {state.phase === "signed-out" ? <SignedOutView onSignIn={handleSignIn} busy={busy} /> : null}
      {authenticated ? (
        <AuthenticatedView identity={state.identity} user={state.user} onSignOut={handleSignOut} />
      ) : null}
      <footer className="reviewer-footer">
        <span>Developed by Gargi Gupta</span>
        <span>B.Tech, MIT Manipal</span>
        <a href="mailto:gargig469@gmail.com">gargig469@gmail.com</a>
      </footer>
    </div>
  );
}
