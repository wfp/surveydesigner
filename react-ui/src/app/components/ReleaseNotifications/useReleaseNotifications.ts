import { useEffect, useRef, useState } from "react";
import {
  clearReleaseNotifications,
  getReleaseNotifications,
  ReleaseListResponse,
  updateRelease,
} from "../../utils/releaseNotifications";

export const RELEASE_POLL_INTERVAL = 5 * 60 * 1000;
const RETRY_INTERVAL = 15 * 1000;
type Action = "read" | "clear";
const empty: ReleaseListResponse = { results: [], unread_count: 0, count: 0 };

export function useReleaseNotifications(
  mode: "recent" | "history" = "recent",
  page = 1,
) {
  const [data, setData] = useState<ReleaseListResponse>(empty);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<"fetch" | Action | null>(null);
  const [open, setOpen] = useState(false);
  const current = useRef(data);
  const pending = useRef<{ ids: number[]; action: Action } | null>(null);
  const controller = useRef<{
    fetch: (force?: boolean) => Promise<void>;
    act: (ids: number[], action: Action) => Promise<void>;
  }>();

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let inFlight: Promise<void> | null = null;
    let actionInFlight = false;
    let failures = 0;
    let retryAfter = 0;
    let revision = 0;
    const requests = new Set<AbortController>();
    const publish = (value: ReleaseListResponse) => {
      current.current = value;
      setData(value);
    };
    publish(empty);
    setLoading(true);
    setError(null);
    pending.current = null;

    const schedule = () => {
      clearTimeout(timer);
      if (active && document.visibilityState !== "hidden") {
        timer = setTimeout(
          () => {
            fetchList();
          },
          failures
            ? Math.max(0, retryAfter - Date.now())
            : RELEASE_POLL_INTERVAL,
        );
      }
    };
    const fetchList = (force = false): Promise<void> => {
      if (inFlight) return inFlight;
      if (!active || (!force && Date.now() < retryAfter))
        return Promise.resolve();
      clearTimeout(timer);
      const request = new AbortController();
      requests.add(request);
      const startRevision = revision;
      inFlight = (async () => {
        try {
          const value = await getReleaseNotifications(
            request.signal,
            mode,
            page,
          );
          if (active) {
            failures = 0;
            retryAfter = 0;
            if (startRevision === revision) publish(value);
            setError((previous) => (previous === "fetch" ? null : previous));
          }
        } catch {
          if (active) {
            failures += 1;
            retryAfter =
              Date.now() +
              Math.min(
                RETRY_INTERVAL * 2 ** (failures - 1),
                RELEASE_POLL_INTERVAL,
              );
            setError((previous) => previous || "fetch");
          }
        } finally {
          requests.delete(request);
          inFlight = null;
          if (active) {
            setLoading(false);
            schedule();
            if (startRevision !== revision) fetchList(true);
          }
        }
      })();
      return inFlight;
    };
    const act = async (ids: number[], action: Action) => {
      if (!active || actionInFlight || ids.length === 0) return;
      actionInFlight = true;
      revision += 1;
      setBusy(true);
      pending.current = { ids, action };
      const request = new AbortController();
      requests.add(request);
      try {
        const changed =
          action === "read"
            ? await updateRelease(ids[0], "read", request.signal)
            : await clearReleaseNotifications(ids, request.signal);
        if (active) {
          revision += 1;
          const previous = current.current;
          const affectedUnread = previous.results.filter(
            (item) => ids.includes(item.id) && item.state === "unread",
          ).length;
          publish({
            ...previous,
            results: previous.results
              .map((item) => {
                if (action === "read")
                  return changed && changed.id === item.id ? changed : item;
                return ids.includes(item.id)
                  ? { ...item, state: "cleared" as const }
                  : item;
              })
              .filter((item) => mode === "history" || item.state !== "cleared"),
            unread_count: Math.max(0, previous.unread_count - affectedUnread),
          });
          pending.current = null;
          setError(null);
          window.dispatchEvent(new Event("release-notifications-changed"));
        }
      } catch {
        if (active) setError(action);
      } finally {
        requests.delete(request);
        actionInFlight = false;
        if (active) {
          setBusy(false);
          fetchList(true);
        }
      }
    };
    controller.current = { fetch: fetchList, act };
    const onVisibleFocus = () => {
      if (document.visibilityState === "hidden") clearTimeout(timer);
      else {
        fetchList();
        schedule();
      }
    };
    const onChange = () => {
      fetchList(true);
    };
    document.addEventListener("visibilitychange", onVisibleFocus);
    window.addEventListener("focus", onVisibleFocus);
    window.addEventListener("release-notifications-changed", onChange);
    fetchList(true);
    return () => {
      active = false;
      clearTimeout(timer);
      requests.forEach((request) => request.abort());
      document.removeEventListener("visibilitychange", onVisibleFocus);
      window.removeEventListener("focus", onVisibleFocus);
      window.removeEventListener("release-notifications-changed", onChange);
    };
  }, [mode, page]);

  return {
    releases: data.results,
    unreadCount: data.unread_count,
    total: data.count || 0,
    loading,
    busy,
    error,
    open,
    openDropdown: () => {
      setOpen(true);
      controller.current?.fetch(true);
    },
    closeDropdown: () => setOpen(false),
    read: (id: number) => {
      controller.current?.act([id], "read");
    },
    clear: () => {
      controller.current?.act(
        current.current.results.map((item) => item.id),
        "clear",
      );
    },
    retry: () => {
      if (error === "fetch") controller.current?.fetch(true);
      else if (pending.current)
        controller.current?.act(pending.current.ids, pending.current.action);
    },
  };
}
