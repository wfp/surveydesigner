import React, { ReactNode, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";
import CookieConsent from "./components/CookieConsent";

import store, { useAppSelector, useAppDispatch } from "./redux/store";
import ScrollToTop from "./utils/scrollToTop";
import { API, VERSION } from "./utils";
import { useTranslation } from "react-i18next";
import { loadUserData } from "./redux/actions/authActions";

if (import.meta.env.PROD) {
  Sentry.init({
    environment: window.env || "local",
    dsn: "https://8c095f18cb924974bd22a2978a7bc6e1@o274918.ingest.sentry.io/4503891341737984",
    tracesSampleRate: 0.001,
    release: VERSION || "0.local",
    integrations: [new BrowserTracing()],
  });
}

interface PrivateRouteProps {
  children: ReactNode;
}

function PrivateRoute({ children }: PrivateRouteProps) {
  const auth = useAppSelector((state) => state.auth);
  const location = useLocation();

  return auth.is_logged ? (
    children
  ) : (
    <Navigate to="/" state={{ from: location }} replace />
  );
}

const { lazy } = React;

const Home = lazy(() => import("./views/Home"));
const SurveyWizard = lazy(() => import("./components/SurveyWizard"));
const ApiKeys = lazy(() => import("./views/APIKeys"));
const Faq = lazy(() => import("./views/Faq"));
const NotFound = lazy(() => import("./views/Error/NotFound"));
const SharedLinkLandingPage = lazy(() => import("./views/SharedLink"));

function App() {
  const { i18n } = useTranslation();
  window.global = window;
  const dispatch = useAppDispatch();

  useEffect(() => {
    API.defaults.headers.common["Accept-Language"] = i18n.language;
  }, [i18n.language]);

  useEffect(() => {
    const interceptor = API.interceptors.request.use((config) => {
      const { surveyForm } = store.getState();
      if (surveyForm.organizations?.length > 0) {
        (config.headers as any)["Survey-Designer-Organizations"] =
          surveyForm.organizations.map(({ id }) => id).toString();
      }
      return config;
    });
    return () => API.interceptors.request.eject(interceptor);
  }, []);

  useEffect(() => {
    dispatch(loadUserData());
  }, [dispatch]);

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ScrollToTop />
      <CookieConsent />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="/design/:step"
          element={
            <PrivateRoute>
              <SurveyWizard />
            </PrivateRoute>
          }
        />
        <Route
          path="/api-keys"
          element={
            <PrivateRoute>
              <ApiKeys />
            </PrivateRoute>
          }
        />
        <Route
          path="/help"
          element={
            <PrivateRoute>
              <Faq />
            </PrivateRoute>
          }
        />
        <Route
          path="/survey/copy/:uuid"
          element={
            <PrivateRoute>
              <SharedLinkLandingPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;
