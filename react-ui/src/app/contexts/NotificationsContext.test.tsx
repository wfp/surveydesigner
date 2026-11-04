import React from "react";
import { Provider } from "react-redux";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestStore } from "../redux/store";
import { authActions } from "../redux/reducers/authReducer";
import {
  NotificationsProvider,
  NOTIFICATION_POLL_MS,
  useNotifications,
} from "./NotificationsContext";
import * as api from "../utils/notifications";

vi.mock("../utils/notifications", () => ({
  fetchNotifications: vi.fn(),
  acknowledgeNotification: vi.fn(),
}));

const notice: api.SurveyNotification = {
  id: 1,
  title: "Update",
  abstract: "Summary",
  language: "en",
  release_id: 2,
  publish_at: "2026-11-03T12:00:00Z",
  expires_at: null,
  is_read: false,
};
const read: api.NotificationAcknowledgement = {
  id: 1,
  state: "read",
  read_at: "2026-11-03T12:01:00Z",
  dismissed: false,
};
const firstUser = { email: "one@example.org", display_name: "One" };
const secondUser = { email: "two@example.org", display_name: "Two" };
const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};
const flush = () =>
  act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
let feed: ReturnType<typeof useNotifications>;
let language: ReturnType<typeof createInstance>;
function Probe() {
  feed = useNotifications();
  return null;
}
function setup(loggedIn = true) {
  const store = createTestStore({
    auth: { is_logged: loggedIn, user: loggedIn ? firstUser : undefined },
  });
  const view = render(
    <Provider store={store}>
      <I18nextProvider i18n={language}>
        <NotificationsProvider>
          <Probe />
        </NotificationsProvider>
      </I18nextProvider>
    </Provider>,
  );
  return { ...view, store };
}
function visibility(value: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  language = createInstance();
  void language.init({
    lng: "en",
    fallbackLng: "en",
    resources: { en: { translation: {} }, fr: { translation: {} } },
    initImmediate: false,
  });
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  vi.mocked(api.fetchNotifications).mockResolvedValue([notice]);
  vi.mocked(api.acknowledgeNotification).mockResolvedValue(read);
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("notification session", () => {
  it("does not request anything while signed out", async () => {
    setup(false);
    act(() => {
      window.dispatchEvent(new Event("focus"));
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS * 2);
    });
    await flush();
    expect(api.fetchNotifications).not.toHaveBeenCalled();
    expect(feed.notifications).toEqual([]);
  });

  it("fetches after authentication and polls every five visible minutes", async () => {
    const { store } = setup(false);
    act(() => {
      store.dispatch(
        authActions.loadUser({ is_logged: true, user: firstUser as never }),
      );
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    expect(feed.notifications).toEqual([notice]);
    act(() => {
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS - 1);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(2);
  });

  it("does not overlap opening, focus, or poll requests", async () => {
    const request = deferred<api.SurveyNotification[]>();
    vi.mocked(api.fetchNotifications).mockReturnValueOnce(request.promise);
    setup();
    act(() => {
      void feed.refresh();
      window.dispatchEvent(new Event("focus"));
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    request.resolve([notice]);
    await flush();
    expect(feed.loading).toBe(false);
  });

  it("pauses hidden tabs, then refreshes when visible or focused", async () => {
    visibility("hidden");
    setup();
    expect(api.fetchNotifications).not.toHaveBeenCalled();
    act(() => visibility("visible"));
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    act(() => visibility("hidden"));
    act(() => {
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS * 3);
      window.dispatchEvent(new Event("focus"));
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    act(() => visibility("visible"));
    await flush();
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(3);
  });

  it("backs off failures and resets after success", async () => {
    vi.mocked(api.fetchNotifications)
      .mockRejectedValueOnce(new Error("offline"))
      .mockRejectedValueOnce(new Error("offline"));
    setup();
    await flush();
    expect(feed.error).toBeTruthy();
    act(() => {
      window.dispatchEvent(new Event("focus"));
      vi.advanceTimersByTime(29999);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(2);
    act(() => {
      vi.advanceTimersByTime(59999);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(2);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(3);
    expect(feed.error).toBeNull();
  });

  it("allows deliberate retry during backoff", async () => {
    vi.mocked(api.fetchNotifications).mockRejectedValueOnce(
      new Error("offline"),
    );
    setup();
    await flush();
    await act(async () => {
      await feed.refresh();
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(2);
    expect(feed.error).toBeNull();
  });

  it("aborts requests and removes listeners and timers on unmount", async () => {
    const request = deferred<api.SurveyNotification[]>();
    vi.mocked(api.fetchNotifications).mockReturnValueOnce(request.promise);
    const { unmount } = setup();
    const signal = vi.mocked(api.fetchNotifications).mock.calls[0][1];
    unmount();
    expect(signal.aborted).toBe(true);
    request.resolve([notice]);
    await flush();
    act(() => {
      window.dispatchEvent(new Event("focus"));
      visibility("visible");
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
  });

  it("discards stale responses after an account change", async () => {
    const old = deferred<api.SurveyNotification[]>();
    vi.mocked(api.fetchNotifications)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce([{ ...notice, id: 2, title: "Second account" }]);
    const { store } = setup();
    act(() => {
      store.dispatch(
        authActions.loadUser({ is_logged: true, user: secondUser as never }),
      );
    });
    await flush();
    old.resolve([notice]);
    await flush();
    expect(feed.account).toBe(secondUser.email);
    expect(feed.notifications.map((item) => item.id)).toEqual([2]);
  });

  it("clears notifications and stops all polling on logout", async () => {
    const { store } = setup();
    await flush();
    act(() => {
      store.dispatch(authActions.clearData());
    });
    expect(feed.notifications).toEqual([]);
    act(() => {
      window.dispatchEvent(new Event("focus"));
      vi.advanceTimersByTime(NOTIFICATION_POLL_MS);
    });
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
  });

  it("only marks read after the server confirms the exact ID", async () => {
    const request = deferred<api.NotificationAcknowledgement>();
    vi.mocked(api.acknowledgeNotification).mockReturnValueOnce(request.promise);
    setup();
    await flush();
    act(() => {
      void feed.acknowledge(1, "read");
    });
    expect(feed.notifications[0].is_read).toBe(false);
    expect(feed.pendingIds).toEqual([1]);
    request.resolve(read);
    await flush();
    expect(feed.notifications[0].is_read).toBe(true);
    expect(feed.pendingIds).toEqual([]);
    expect(api.acknowledgeNotification).toHaveBeenCalledWith(
      1,
      "read",
      expect.any(AbortSignal),
    );
  });

  it("retains state after failed read/dismiss and allows retry", async () => {
    vi.mocked(api.acknowledgeNotification)
      .mockRejectedValueOnce(new Error("failed"))
      .mockRejectedValueOnce(new Error("failed"));
    setup();
    await flush();
    await act(async () => {
      await feed.acknowledge(1, "read");
      await feed.acknowledge(1, "dismiss");
    });
    expect(feed.notifications).toEqual([notice]);
    expect(feed.actionError).toBeTruthy();
    vi.mocked(api.acknowledgeNotification).mockResolvedValueOnce({
      ...read,
      state: "dismissed",
      dismissed: true,
    });
    await act(async () => {
      await feed.acknowledge(1, "dismiss");
    });
    expect(feed.notifications).toEqual([]);
    expect(feed.actionError).toBeNull();
  });

  it("cannot restore a dismissed notification from a stale GET", async () => {
    setup();
    await flush();
    const old = deferred<api.SurveyNotification[]>();
    vi.mocked(api.fetchNotifications)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce([]);
    act(() => {
      void feed.refresh();
    });
    vi.mocked(api.acknowledgeNotification).mockResolvedValueOnce({
      ...read,
      state: "dismissed",
      dismissed: true,
    });
    await act(async () => {
      await feed.acknowledge(1, "dismiss");
    });
    old.resolve([notice]);
    await flush();
    expect(feed.notifications).toEqual([]);
    act(() => {
      vi.advanceTimersByTime(0);
    });
    await flush();
    expect(api.fetchNotifications).toHaveBeenCalledTimes(3);
    expect(feed.notifications).toEqual([]);
  });

  it("leaves newly polled notifications unread without acknowledging them", async () => {
    setup();
    await flush();
    vi.mocked(api.fetchNotifications).mockResolvedValueOnce([
      { ...notice, id: 2 },
      notice,
    ]);
    await act(async () => {
      await feed.refresh();
    });
    expect(feed.notifications.every((item) => !item.is_read)).toBe(true);
    expect(api.acknowledgeNotification).not.toHaveBeenCalled();
  });

  it("deduplicates repeated reads and serializes dismissal for the same ID", async () => {
    const request = deferred<api.NotificationAcknowledgement>();
    vi.mocked(api.acknowledgeNotification)
      .mockReturnValueOnce(request.promise)
      .mockResolvedValueOnce({ ...read, state: "dismissed", dismissed: true });
    setup();
    await flush();
    act(() => {
      void feed.acknowledge(1, "read");
      void feed.acknowledge(1, "read");
      void feed.acknowledge(1, "dismiss");
    });
    expect(api.acknowledgeNotification).toHaveBeenCalledTimes(1);
    request.resolve(read);
    await flush();
    await flush();
    expect(api.acknowledgeNotification).toHaveBeenCalledTimes(2);
    expect(feed.notifications).toEqual([]);
  });

  it("refetches translated content and discards the old language response", async () => {
    const old = deferred<api.SurveyNotification[]>();
    vi.mocked(api.fetchNotifications)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce([
        { ...notice, title: "Mise a jour", language: "fr" },
      ]);
    setup();
    await act(async () => {
      await language.changeLanguage("fr");
    });
    await flush();
    old.resolve([notice]);
    await flush();
    expect(feed.language).toBe("fr");
    expect(feed.notifications[0].title).toBe("Mise a jour");
  });

  it("reconciles read/dismiss changes made on another device", async () => {
    setup();
    await flush();
    vi.mocked(api.fetchNotifications)
      .mockResolvedValueOnce([{ ...notice, is_read: true }])
      .mockResolvedValueOnce([]);
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(feed.notifications[0].is_read).toBe(true);
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(feed.notifications).toEqual([]);
  });
});
