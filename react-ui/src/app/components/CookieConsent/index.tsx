import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button, Link, Modal, Checkbox, Callout } from "@wfp/react";
import { clarity } from "react-microsoft-clarity";
import {
  disableGoogleAnalytics,
  enableGoogleAnalyticsForCurrentPage,
} from "../../utils/googleAnalytics";

// --- Types & defaults ---
export type ConsentCategory = "essential" | "analytics";
export type ConsentRecord = Record<ConsentCategory, boolean> & {
  [k: string]: boolean;
};
const DEFAULT_CONSENT: ConsentRecord = { essential: true, analytics: false };
const CLARITY_PROJECT_ID = import.meta.env.VITE_CLARITY_PROJECT_ID;

export interface CookieConsentProps {
  policyUrl?: string; // Link to your cookie policy
  onConsentChange?: (c: ConsentRecord) => void; // Callback whenever consent is saved/changed
  storageKey?: string; // localStorage key for persistence
  cookieName?: string; // Optional: cookie for backend/SSR awareness
  maxAgeDays?: number; // Cookie lifetime
  showManageFloatingButton?: boolean; // Floating “Cookie settings” button after a choice
}

// --- Storage helpers ---
function readStoredConsent(storageKey: string): ConsentRecord | null {
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object"
      ? ({ ...DEFAULT_CONSENT, ...parsed } as ConsentRecord)
      : null;
  } catch {
    return null;
  }
}

function writeStoredConsent(storageKey: string, consent: ConsentRecord) {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(consent));
  } catch {
    /* ignore */
  }
}

// Write a small cookie so the backend can read consent (optional; keep if you need it)
function writeConsentCookie(
  cookieName: string,
  consent: ConsentRecord,
  maxAgeDays: number,
) {
  const sorted = Object.keys(consent)
    .sort()
    .reduce((acc: ConsentRecord, k) => {
      acc[k] = consent[k as keyof ConsentRecord];
      return acc;
    }, {} as ConsentRecord);
  const value = encodeURIComponent(JSON.stringify(sorted));
  const maxAge = Math.floor(maxAgeDays * 24 * 60 * 60);
  const secure = location.protocol === "https:" ? "; Secure" : ""; // allow on localhost http
  document.cookie = `${cookieName}=${value}; Max-Age=${maxAge}; Path=/; SameSite=Lax${secure}`;
}

// Send the consent update to analytics providers once their stubs are available
function sendAnalyticsConsent(consent: ConsentRecord) {
  if (consent.analytics) {
    enableGoogleAnalyticsForCurrentPage();

    if (CLARITY_PROJECT_ID) {
      if (!clarity.hasStarted()) {
        clarity.init(CLARITY_PROJECT_ID);
      } else {
        clarity.start();
      }
      clarity.consent(true);
    }
    return;
  }

  disableGoogleAnalytics();
  if (clarity.hasStarted()) {
    clarity.consent(false);
    clarity.stop();
  }
}

const CookieConsentBanner: React.FC<CookieConsentProps> = ({
  policyUrl = "/privacy#cookies",
  onConsentChange,
  storageKey = "cookie-consent.v1",
  cookieName = "cookie_consent",
  maxAgeDays = 365,
  showManageFloatingButton = true,
}) => {
  // Read once on mount; banner shows only if no stored choice
  const initial = useMemo(() => readStoredConsent(storageKey), [storageKey]);
  const [consent, setConsent] = useState<ConsentRecord | null>(initial);
  const [showBanner, setShowBanner] = useState<boolean>(!initial);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [draft, setDraft] = useState<ConsentRecord>(initial || DEFAULT_CONSENT);

  useEffect(() => {
    // expose an imperative helper for other components
    (window as any).openCookieSettings = () => {
      setDraft(consent || DEFAULT_CONSENT);
      setShowModal(true);
    };

    // support a custom DOM event for decoupled usage
    const handler = () => (window as any).openCookieSettings();
    window.addEventListener("open-cookie-settings", handler);
    return () => {
      delete (window as any).openCookieSettings;
      window.removeEventListener("open-cookie-settings", handler);
    };
  }, [consent]);

  // Persist + notify + tell analytics providers whenever consent changes
  useEffect(() => {
    if (!consent) return;
    writeStoredConsent(storageKey, consent);
    writeConsentCookie(cookieName, consent, maxAgeDays);
    sendAnalyticsConsent(consent);
    onConsentChange?.(consent);
  }, [consent, cookieName, maxAgeDays, onConsentChange, storageKey]);

  // Quick actions
  const acceptAll = () => {
    setConsent({ essential: true, analytics: true });
    setShowBanner(false);
    setShowModal(false);
  };
  const rejectAll = () => {
    setConsent({ essential: true, analytics: false });
    setShowBanner(false);
    setShowModal(false);
  };
  const savePreferences = () => {
    setConsent({ ...draft, essential: true });
    setShowBanner(false);
    setShowModal(false);
  };
  const openManage = () => {
    setDraft(consent || DEFAULT_CONSENT);
    setShowModal(true);
  };

  // Accessibility nicety: focus first action when banner appears
  const firstButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (showBanner) firstButtonRef.current?.focus();
  }, [showBanner]);

  // Push page content up while banner is visible (avoid covering footer)
  const bannerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!showBanner || !bannerRef.current) return;
    const el = bannerRef.current;
    const applyPadding = () =>
      (document.body.style.paddingBottom = `${(el.offsetHeight || 0) + 8}px`);
    applyPadding();
    const ro = (window as any).ResizeObserver
      ? new (window as any).ResizeObserver(applyPadding)
      : null;
    ro?.observe(el);
    return () => {
      ro?.disconnect?.();
      document.body.style.paddingBottom = "";
    };
  }, [showBanner]);

  return (
    <>
      {/* Banner */}
      {showBanner && (
        <div
          ref={bannerRef}
          role="region"
          aria-label="Cookie consent"
          className="wfp--layer"
          style={{
            position: "fixed",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999,
            padding: "0.75rem",
          }}
        >
          <div
            className="wfp--tile"
            style={{
              maxWidth: 1280,
              margin: "0 auto",
              boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
            }}
          >
            <Callout
              kind="info"
              title="Cookies on this site"
              role="region"
              style={{ margin: 0 }}
            >
              <div className="wfp--grid" style={{ padding: "0.75rem 0" }}>
                <div
                  className="wfp--row"
                  style={{ alignItems: "center", rowGap: "0.5rem" }}
                >
                  {/* Text */}
                  <div className="wfp--col-lg-9 wfp--col-md-8 wfp--col-sm-12">
                    We use <strong>essential</strong> cookies to make this site
                    work. We’d also like to use
                    <strong> analytics</strong> cookies (Google Analytics and
                    Microsoft Clarity) to improve your experience. You can
                    change your choices at any time. See our{" "}
                    <Link
                      href={policyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      cookie policy
                    </Link>
                    .
                  </div>
                  {/* Actions */}
                  <div
                    className="wfp--col-lg-3 wfp--col-md-4 wfp--col-sm-12"
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      alignItems: "center",
                      gap: "0.5rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <Button
                      ref={firstButtonRef}
                      kind="secondary"
                      onClick={rejectAll}
                    >
                      Reject analytics
                    </Button>
                    <Button kind="secondary" onClick={openManage}>
                      Manage cookies
                    </Button>
                    <Button kind="primary" onClick={acceptAll}>
                      Accept analytics
                    </Button>
                  </div>
                </div>
              </div>
            </Callout>
          </div>
        </div>
      )}

      {/* Manage modal */}
      <Modal
        primaryButtonText="Save preferences"
        secondaryButtonText="Cancel"
        modalHeading="Manage cookie preferences"
        open={showModal}
        onRequestClose={() => setShowModal(false)}
        onRequestSubmit={savePreferences}
        onSecondarySubmit={() => setShowModal(false)}
      >
        <div className="wfp--form-item" style={{ marginBottom: "0.5rem" }}>
          <Checkbox
            id="consent-essential"
            checked
            disabled
            labelText={
              <span>
                Essential cookies{" "}
                <span style={{ fontWeight: 400 }}>(always on)</span>
              </span>
            }
          />
          <p className="wfp--label-description">
            Required for basic site functionality and security.
          </p>
        </div>

        <div className="wfp--form-item" style={{ marginBottom: "0.5rem" }}>
          <Checkbox
            id="consent-analytics"
            checked={draft.analytics}
            // Works with Carbon/WFP Checkbox which can pass (checked:boolean) or an event
            onChange={(checkedOrEvent: any) => {
              const checked =
                typeof checkedOrEvent === "boolean"
                  ? checkedOrEvent
                  : !!checkedOrEvent?.target?.checked;
              setDraft((d) => ({ ...d, analytics: checked }));
            }}
            labelText="Analytics cookies"
          />
          <p className="wfp--label-description">
            Help us understand how you use the site to improve it (Google
            Analytics and Microsoft Clarity).
          </p>
        </div>
      </Modal>
    </>
  );
};

export default CookieConsentBanner;
