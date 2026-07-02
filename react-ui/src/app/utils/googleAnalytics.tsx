const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;
const GA_SCRIPT_ID = "google-analytics-gtag";
let analyticsEnabled = false;
let isConfigured = false;

function hasMeasurementId() {
  return !!GA_MEASUREMENT_ID;
}

function gtag(...args: unknown[]) {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push(args);
}

function ensureGtag() {
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || gtag;
  return window.gtag;
}

function setGoogleAnalyticsDisabled(disabled: boolean) {
  if (!hasMeasurementId()) return;
  (window as any)[`ga-disable-${GA_MEASUREMENT_ID}`] = disabled;
}

function setAnalyticsConsent(granted: boolean) {
  ensureGtag()("consent", "update", {
    analytics_storage: granted ? "granted" : "denied",
  });
}

function addGoogleAnalyticsScript() {
  if (document.getElementById(GA_SCRIPT_ID)) return;

  const script = document.createElement("script");
  script.id = GA_SCRIPT_ID;
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);
}

export function initGoogleAnalytics() {
  if (!hasMeasurementId()) return;

  analyticsEnabled = true;
  setGoogleAnalyticsDisabled(false);

  if (!isConfigured) {
    ensureGtag()("consent", "default", {
      analytics_storage: "denied",
    });
    ensureGtag()("js", new Date());
    ensureGtag()("config", GA_MEASUREMENT_ID, {
      send_page_view: false,
    });
    addGoogleAnalyticsScript();
    isConfigured = true;
  }

  setAnalyticsConsent(true);
}

export function disableGoogleAnalytics() {
  if (!hasMeasurementId()) return;

  analyticsEnabled = false;
  ensureGtag();
  setAnalyticsConsent(false);
  setGoogleAnalyticsDisabled(true);
}

export function trackGoogleAnalyticsPageView(path: string) {
  if (!hasMeasurementId() || !analyticsEnabled || !window.gtag) return;

  window.gtag("event", "page_view", {
    page_location: window.location.href,
    page_path: path,
    page_title: document.title,
  });
}

export function enableGoogleAnalyticsForCurrentPage() {
  initGoogleAnalytics();
  trackGoogleAnalyticsPageView(
    `${window.location.pathname}${window.location.search}`,
  );
}
