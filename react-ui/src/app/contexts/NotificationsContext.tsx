import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../redux/store";
import {
  acknowledgeNotification,
  fetchNotifications,
  NotificationAcknowledgement,
  NotificationAction,
  SurveyNotification,
} from "../utils/notifications";

export const NOTIFICATION_POLL_MS = 5 * 60 * 1000;
const RETRY_MS = 30 * 1000;

interface FeedState {
  notifications: SurveyNotification[];
  loading: boolean;
  error: unknown;
  actionError: unknown;
  pendingIds: number[];
}
interface FeedContext extends FeedState {
  account: string | null;
  language: string;
  refresh: () => Promise<void>;
  acknowledge: (
    id: number,
    action: NotificationAction,
  ) => Promise<NotificationAcknowledgement | null>;
}
const emptyState: FeedState = {
  notifications: [],
  loading: false,
  error: null,
  actionError: null,
  pendingIds: [],
};
const NotificationsContext = createContext<FeedContext>({
  ...emptyState,
  account: null,
  language: "en",
  refresh: () => Promise.resolve(),
  acknowledge: async () => null,
});
export const useNotifications = () => useContext(NotificationsContext);

function NotificationSession({
  account,
  language,
  children,
}: PropsWithChildren<{ account: string | null; language: string }>) {
  const [state, setState] = useState<FeedState>({
    ...emptyState,
    loading: !!account,
  });
  const controls = useRef<Pick<FeedContext, "refresh" | "acknowledge"> | null>(
    null,
  );

  useEffect(() => {
    if (!account) return undefined;
    setState({ ...emptyState, loading: true });
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let inFlight: Promise<void> | null = null;
    let failures = 0;
    let retryAt = 0;
    let revision = 0;
    const requests = new Set<AbortController>();
    const pending = new Map<
      number,
      {
        action: NotificationAction;
        promise: Promise<NotificationAcknowledgement | null>;
      }
    >();
    const visible = () => document.visibilityState !== "hidden";
    const stopTimer = () => {
      clearTimeout(timer);
      timer = undefined;
    };
    const schedule = (delay: number) => {
      stopTimer();
      if (active && visible())
        timer = setTimeout(() => {
          load();
        }, delay);
    };
    const load = (deliberate = false): Promise<void> => {
      if (!active || !visible()) return Promise.resolve();
      if (inFlight) return inFlight;
      if (!deliberate && retryAt > Date.now()) {
        schedule(retryAt - Date.now());
        return Promise.resolve();
      }
      stopTimer();
      const controller = new AbortController();
      requests.add(controller);
      const startedRevision = revision;
      let rerun = false;
      setState((current) => ({ ...current, loading: true }));
      inFlight = (async () => {
        try {
          const notifications = await fetchNotifications(
            language,
            controller.signal,
          );
          if (!active) return;
          failures = 0;
          retryAt = 0;
          if (startedRevision !== revision) rerun = true;
          else
            setState((current) => ({ ...current, notifications, error: null }));
        } catch (error) {
          if (!active || controller.signal.aborted) return;
          failures += 1;
          retryAt =
            Date.now() +
            Math.min(
              RETRY_MS * 2 ** Math.min(failures - 1, 4),
              NOTIFICATION_POLL_MS,
            );
          setState((current) => ({ ...current, error }));
        } finally {
          requests.delete(controller);
          inFlight = null;
          if (active) {
            setState((current) => ({ ...current, loading: false }));
            schedule(
              rerun
                ? 0
                : Math.max(
                    retryAt - Date.now(),
                    failures ? 0 : NOTIFICATION_POLL_MS,
                  ),
            );
          }
        }
      })();
      return inFlight;
    };

    const acknowledge: FeedContext["acknowledge"] = (id, action) => {
      if (!active) return Promise.resolve(null);
      const existing = pending.get(id);
      if (existing) {
        if (existing.action === action) return existing.promise;
        return existing.promise.then(() => acknowledge(id, action));
      }
      const controller = new AbortController();
      requests.add(controller);
      setState((current) => ({
        ...current,
        actionError: null,
        pendingIds: [...current.pendingIds, id],
      }));
      const promise = (async () => {
        try {
          const result = await acknowledgeNotification(
            id,
            action,
            controller.signal,
          );
          if (!active) return null;
          revision += 1;
          setState((current) => ({
            ...current,
            notifications: result.dismissed
              ? current.notifications.filter((item) => item.id !== id)
              : current.notifications.map((item) =>
                  item.id === id ? { ...item, is_read: true } : item,
                ),
          }));
          return result;
        } catch (error) {
          if (active && !controller.signal.aborted)
            setState((current) => ({ ...current, actionError: error }));
          return null;
        } finally {
          requests.delete(controller);
          pending.delete(id);
          if (active)
            setState((current) => ({
              ...current,
              pendingIds: current.pendingIds.filter((item) => item !== id),
            }));
        }
      })();
      pending.set(id, { action, promise });
      return promise;
    };
    const resume = () => {
      if (visible()) load();
      else stopTimer();
    };
    controls.current = { refresh: () => load(true), acknowledge };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    load();
    return () => {
      active = false;
      controls.current = null;
      stopTimer();
      requests.forEach((controller) => controller.abort());
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
    };
  }, [account, language]);

  const refresh = useCallback(
    () => controls.current?.refresh() ?? Promise.resolve(),
    [],
  );
  const acknowledge = useCallback<FeedContext["acknowledge"]>(
    (id, action) =>
      controls.current?.acknowledge(id, action) ?? Promise.resolve(null),
    [],
  );
  const value = useMemo(
    () => ({ ...state, account, language, refresh, acknowledge }),
    [state, account, language, refresh, acknowledge],
  );
  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function NotificationsProvider({ children }: PropsWithChildren) {
  const auth = useAppSelector((store) => store.auth);
  const { i18n } = useTranslation();
  const account = auth.is_logged ? auth.user?.email || null : null;
  const language = i18n.resolvedLanguage || i18n.language || "en";
  // Replacing the session also removes old rendered content before new effects run.
  return (
    <NotificationSession
      key={account || "signed-out"}
      account={account}
      language={language}
    >
      {children}
    </NotificationSession>
  );
}
