/*
 * Survey Designer
 * Copyright (C) 2026 World Food Programme
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React, { ReactNode, useEffect, useState } from "react";
import { Loading } from "@wfp/react";
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
import { NotificationsProvider } from "./contexts/NotificationsContext";

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
  ready: boolean;
}

function PrivateRoute({ children, ready }: PrivateRouteProps) {
  const auth = useAppSelector((state) => state.auth);
  const location = useLocation();

  if (!ready) return <Loading withOverlay small={false} />;

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
const NotificationsPage = lazy(() => import("./views/Notifications"));
const NotificationContentPage = lazy(() =>
  import("./views/Notifications").then((module) => ({
    default: module.NotificationContentPage,
  })),
);

function App() {
  const { i18n } = useTranslation();
  window.global = window;
  const dispatch = useAppDispatch();
  const [authReady, setAuthReady] = useState(false);

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
    let active = true;
    dispatch(loadUserData()).finally(() => {
      if (active) setAuthReady(true);
    });
    return () => {
      active = false;
    };
  }, [dispatch]);

  return (
    <Router>
      <ScrollToTop />
      <CookieConsent />
      <NotificationsProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/design/:step"
            element={
              <PrivateRoute ready={authReady}>
                <SurveyWizard />
              </PrivateRoute>
            }
          />
          <Route
            path="/api-keys"
            element={
              <PrivateRoute ready={authReady}>
                <ApiKeys />
              </PrivateRoute>
            }
          />
          <Route
            path="/help"
            element={
              <PrivateRoute ready={authReady}>
                <Faq />
              </PrivateRoute>
            }
          />
          <Route
            path="/survey/copy/:uuid"
            element={
              <PrivateRoute ready={authReady}>
                <SharedLinkLandingPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <PrivateRoute ready={authReady}>
                <NotificationsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/notifications/:id"
            element={
              <PrivateRoute ready={authReady}>
                <NotificationContentPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/releases/:id"
            element={
              <PrivateRoute ready={authReady}>
                <NotificationContentPage release />
              </PrivateRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </NotificationsProvider>
    </Router>
  );
}

export default App;
