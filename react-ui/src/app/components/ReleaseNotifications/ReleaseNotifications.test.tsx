import React from "react";
import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render as renderUI,
  screen,
  waitFor,
} from "../../utils/tests";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../../locales/en/translations.json";
import ReleaseNotifications, { ReleaseNotificationBell } from "./index";
import Notifications from "../../views/Notifications";
import {
  getReleaseNotifications,
  updateRelease,
  clearReleaseNotifications,
  ReleaseNotification,
  ReleaseListResponse,
} from "../../utils/releaseNotifications";
import { RELEASE_POLL_INTERVAL } from "./useReleaseNotifications";

vi.mock("../../utils/releaseNotifications", () => ({
  getReleaseNotifications: vi.fn(),
  updateRelease: vi.fn(),
  clearReleaseNotifications: vi.fn(),
}));
let account = { is_logged: true, user: { email: "first@example.com" } };
vi.mock("../../redux/store", () => ({
  useAppSelector: (selector: (state: unknown) => unknown) =>
    selector({ auth: account }),
}));
vi.mock("../Layout", () => ({
  default: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, unknown>) => {
      const name = key.split(".")[1];
      const text =
        key === "actions.close"
          ? "Close"
          : key === "actions.next"
            ? "Next"
            : key === "actions.previous"
              ? "Previous"
              : en.releaseNotifications[
                  name as keyof typeof en.releaseNotifications
                ];
      return (text || key).replace(/{{(.*?)}}/g, (_, value) =>
        String(values?.[value] || ""),
      );
    },
    i18n: { language: "en", resolvedLanguage: "en" },
  }),
}));

const event: ReleaseNotification = {
  id: 1,
  version: "12.9.3",
  description: "Improved survey validation.\nExternal choice-file checks.",
  deployed_at: "2026-10-06T10:30:00Z",
  state: "unread",
};
let events: ReleaseNotification[] = [];
const render = (ui: React.ReactElement) =>
  renderUI(ui, {
    wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter>,
  });
const data = (): ReleaseListResponse => ({
  results: events.filter((item) => item.state !== "cleared"),
  unread_count: events.filter((item) => item.state === "unread").length,
});
const fetchRelease = vi.mocked(getReleaseNotifications);
const changeRelease = vi.mocked(updateRelease);
const clearReleases = vi.mocked(clearReleaseNotifications);
const settle = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};
const clickBell = () =>
  fireEvent.click(screen.getByRole("button", { name: /Latest changes/ }));
const readFirst = () =>
  fireEvent.click(screen.getByRole("button", { name: "Version 12.9.3" }));

beforeEach(() => {
  vi.clearAllMocks();
  account = { is_logged: true, user: { email: "first@example.com" } };
  events = [{ ...event }];
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  fetchRelease.mockImplementation(async () => data());
  changeRelease.mockImplementation(async (id) => {
    events = events.map((item) =>
      item.id === id ? { ...item, state: "read" } : item,
    );
    return events.find((item) => item.id === id) || null;
  });
  clearReleases.mockImplementation(async (ids) => {
    events = events.map((item) =>
      ids.includes(item.id) ? { ...item, state: "cleared" } : item,
    );
  });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("release notifications and history", () => {
  it("does not request notifications when signed out", () => {
    account.is_logged = false;
    render(<ReleaseNotifications />);
    expect(fetchRelease).not.toHaveBeenCalled();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps read and unread releases in the panel and reads only the clicked entry", async () => {
    events.push({ ...event, id: 2, version: "12.9.2", state: "read" });
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    expect(changeRelease).not.toHaveBeenCalled();
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.getByText("Read")).toBeInTheDocument();
    const localTime = new Intl.DateTimeFormat("en", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(event.deployed_at));
    expect(screen.getAllByText(localTime)).toHaveLength(2);
    readFirst();
    await settle();
    expect(changeRelease).toHaveBeenCalledWith(
      1,
      "read",
      expect.any(AbortSignal),
    );
    expect(
      screen.getByRole("button", { name: "Version 12.9.3" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Read")).toHaveLength(2);
    expect(
      screen.queryByTestId("release-unread-marker"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View all notifications" }),
    ).toHaveAttribute("href", "/notifications");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Latest changes" }),
    ).toHaveFocus();
  });

  it("a release discovered while open remains unread until clicked", async () => {
    events[0].state = "read";
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    events.unshift({ ...event, id: 2, version: "12.9.4" });
    fireEvent(window, new Event("focus"));
    await settle();
    expect(screen.getByTestId("release-unread-marker")).toBeInTheDocument();
    expect(changeRelease).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Version 12.9.4" }));
    await settle();
    expect(changeRelease).toHaveBeenCalledWith(
      2,
      "read",
      expect.any(AbortSignal),
    );
    expect(
      screen.getByRole("button", { name: "Version 12.9.4" }),
    ).toBeInTheDocument();
  });

  it("failed read keeps the entry new and offers retry", async () => {
    changeRelease.mockRejectedValueOnce(new Error("offline"));
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    readFirst();
    await settle();
    expect(screen.getByRole("alert")).toHaveTextContent("Could not mark");
    expect(screen.getByText("New")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await settle();
    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("clears the exact visible IDs only after success, with retry after failure", async () => {
    events.push({ ...event, id: 2, version: "12.9.2", state: "read" });
    clearReleases.mockRejectedValueOnce(new Error("offline"));
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    fireEvent.click(
      screen.getByRole("button", { name: "Clear notifications" }),
    );
    await settle();
    expect(clearReleases).toHaveBeenCalledWith([1, 2], expect.any(AbortSignal));
    expect(screen.getByRole("alert")).toHaveTextContent("Could not clear");
    expect(
      screen.getByRole("button", { name: "Version 12.9.3" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await settle();
    expect(
      screen.getByText("No new release notifications."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View all notifications" }),
    ).toBeInTheDocument();
  });

  it("polls every five visible minutes and reconciles another device's read", async () => {
    vi.useFakeTimers();
    render(<ReleaseNotificationBell />);
    await settle();
    events[0].state = "read";
    await act(async () => {
      vi.advanceTimersByTime(RELEASE_POLL_INTERVAL);
    });
    expect(fetchRelease).toHaveBeenCalledTimes(2);
    expect(
      screen.queryByTestId("release-unread-marker"),
    ).not.toBeInTheDocument();
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    fireEvent(document, new Event("visibilitychange"));
    await act(async () => {
      vi.advanceTimersByTime(RELEASE_POLL_INTERVAL * 2);
    });
    expect(fetchRelease).toHaveBeenCalledTimes(2);
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    fireEvent(document, new Event("visibilitychange"));
    await settle();
    expect(fetchRelease).toHaveBeenCalledTimes(3);
  });

  it("backs off failures and prevents overlapping fetches", async () => {
    vi.useFakeTimers();
    fetchRelease.mockRejectedValueOnce(new Error("offline"));
    const { unmount } = render(<ReleaseNotificationBell />);
    await settle();
    fireEvent(window, new Event("focus"));
    expect(fetchRelease).toHaveBeenCalledTimes(1);
    fetchRelease.mockImplementationOnce(() => new Promise(() => {}));
    await act(async () => {
      vi.advanceTimersByTime(15000);
    });
    fireEvent(window, new Event("focus"));
    expect(fetchRelease).toHaveBeenCalledTimes(2);
    unmount();
    expect(fetchRelease.mock.calls[1][0].aborted).toBe(true);
  });

  it("ignores an old account response and aborts requests on logout", async () => {
    let finish: (value: ReleaseListResponse) => void = () => {};
    fetchRelease.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { rerender } = render(<ReleaseNotifications />);
    account = { is_logged: true, user: { email: "second@example.com" } };
    events = [{ ...event, version: "ACCOUNT-B" }];
    rerender(<ReleaseNotifications />);
    await settle();
    finish({ results: [event], unread_count: 1 });
    await settle();
    clickBell();
    await settle();
    expect(
      screen.getByRole("button", { name: "Version ACCOUNT-B" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Version 12.9.3" }),
    ).not.toBeInTheDocument();
    expect(fetchRelease.mock.calls[0][0].aborted).toBe(true);
    account.is_logged = false;
    rerender(<ReleaseNotifications />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("stale fetch cannot undo a successful read", async () => {
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    let finish: (value: ReleaseListResponse) => void = () => {};
    fetchRelease.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent(window, new Event("focus"));
    readFirst();
    await settle();
    finish({ results: [event], unread_count: 1 });
    await settle();
    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(
      screen.queryByTestId("release-unread-marker"),
    ).not.toBeInTheDocument();
  });

  it("fetch errors have retry without an incorrect empty-state claim", async () => {
    fetchRelease.mockRejectedValue(new Error("offline"));
    render(<ReleaseNotificationBell />);
    await settle();
    clickBell();
    await settle();
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load");
    expect(
      screen.queryByText("No new release notifications."),
    ).not.toBeInTheDocument();
    fetchRelease.mockResolvedValue({ results: [], unread_count: 0 });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await settle();
    expect(
      screen.getByText("No new release notifications."),
    ).toBeInTheDocument();
  });

  it("history includes cleared releases and marks an entry read without removing it", async () => {
    events = [event, { ...event, id: 2, version: "OLD", state: "cleared" }];
    fetchRelease.mockImplementation(async () => ({
      results: events,
      unread_count: events.filter((item) => item.state === "unread").length,
      count: 2,
    }));
    render(<Notifications />);
    await settle();
    expect(fetchRelease).toHaveBeenCalledWith(
      expect.any(AbortSignal),
      "history",
      1,
    );
    expect(
      screen.getByRole("button", { name: "Version OLD" }),
    ).toBeInTheDocument();
    readFirst();
    await settle();
    expect(
      screen.getByRole("button", { name: "Version 12.9.3" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Read")).toHaveLength(2);
  });

  it("history requests the next page with the library pagination", async () => {
    fetchRelease.mockImplementation(async (_, mode, page) => ({
      results: [
        { ...event, version: page === 2 ? "SECOND-PAGE" : "FIRST-PAGE" },
      ],
      unread_count: 1,
      count: 25,
    }));
    render(<Notifications />);
    await settle();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await settle();
    expect(fetchRelease).toHaveBeenCalledWith(
      expect.any(AbortSignal),
      "history",
      2,
    );
    expect(
      screen.getByRole("button", { name: "Version SECOND-PAGE" }),
    ).toBeInTheDocument();
  });
});
