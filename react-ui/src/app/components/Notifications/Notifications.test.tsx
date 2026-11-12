import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import translations from "../../../locales/en/translations.json";
import { createTestStore } from "../../redux/store";
import { NotificationsProvider } from "../../contexts/NotificationsContext";
import * as api from "../../utils/notifications";
import NotificationBell from ".";
import Nav from "../Nav";
import NotificationsPage, {
  NotificationContentPage,
} from "../../views/Notifications";

vi.mock("../../utils/notifications", async () => ({
  ...(await vi.importActual<object>("../../utils/notifications")),
  fetchNotifications: vi.fn(),
  fetchNotification: vi.fn(),
  fetchRelease: vi.fn(),
  acknowledgeNotification: vi.fn(),
}));
vi.mock("../Layout", () => ({
  default: ({ children }: React.PropsWithChildren) => <main>{children}</main>,
}));
const notice: api.NotificationDetail = {
  id: 1,
  release_id: 2,
  language: "en",
  title: "Validation improved",
  abstract: "Survey checks",
  body: "<p><strong>Safer surveys</strong></p>",
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
const release: api.ReleaseDetail = {
  id: 2,
  business_version: "2.1.0",
  language: "en",
  title: "Release 2.1.0",
  body: "<p>Release improvements</p>",
  released_at: "2026-11-03T12:00:00Z",
  published_at: "2026-11-03T12:00:00Z",
};
function setup({ loggedIn = true, path = "/", nav = false } = {}) {
  const i18n = createInstance();
  void i18n.init({
    lng: "en",
    resources: { en: { translation: translations } },
    initImmediate: false,
  });
  const store = createTestStore({
    auth: {
      is_logged: loggedIn,
      user: { email: "test@example.org", display_name: "Tester" },
    },
  });
  return render(
    <Provider store={store}>
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={[path]}>
          <NotificationsProvider>
            {nav ? <Nav /> : <NotificationBell />}
            <button type="button">Outside</button>
            <Routes>
              <Route path="/" element={<div />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route
                path="/notifications/:id"
                element={<NotificationContentPage />}
              />
              <Route
                path="/releases/:id"
                element={<NotificationContentPage release />}
              />
            </Routes>
          </NotificationsProvider>
        </MemoryRouter>
      </I18nextProvider>
    </Provider>,
  );
}
const bell = () => screen.getByRole("button", { name: /Notifications/ });
beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  vi.mocked(api.fetchNotifications).mockResolvedValue([notice]);
  vi.mocked(api.fetchNotification).mockResolvedValue(notice);
  vi.mocked(api.fetchRelease).mockResolvedValue(release);
  vi.mocked(api.acknowledgeNotification).mockResolvedValue(read);
});
afterEach(cleanup);

describe("notification UI", () => {
  it("hides the bell and makes no requests for signed-out users", async () => {
    setup({ loggedIn: false, nav: true });
    expect(
      screen.queryByRole("button", { name: /Notifications/ }),
    ).not.toBeInTheDocument();
    expect(api.fetchNotifications).not.toHaveBeenCalled();
  });

  it("opens a labelled panel with unread state without marking anything read", async () => {
    setup();
    await screen.findByRole("button", { name: "Notifications: 1 unread" });
    fireEvent.click(bell());
    expect(
      await screen.findByRole("region", { name: "Notifications" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: notice.title }),
    ).toBeInTheDocument();
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(bell()).toHaveAttribute("aria-expanded", "true");
    expect(api.acknowledgeNotification).not.toHaveBeenCalled();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(bell()).toHaveFocus();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("closes on outside click or keyboard focus leaving the panel", async () => {
    setup();
    await screen.findByRole("button", { name: "Notifications: 1 unread" });
    fireEvent.click(bell());
    fireEvent.mouseDown(document.body);
    expect(bell()).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(bell());
    act(() => screen.getByRole("button", { name: "Outside" }).focus());
    expect(bell()).toHaveAttribute("aria-expanded", "false");
  });

  it("opens the exact notification, marks it read, and retains it in the list", async () => {
    vi.mocked(api.acknowledgeNotification).mockImplementationOnce(async () => {
      vi.mocked(api.fetchNotifications).mockResolvedValue([
        { ...notice, is_read: true },
      ]);
      return read;
    });
    setup();
    await screen.findByRole("button", { name: "Notifications: 1 unread" });
    fireEvent.click(bell());
    fireEvent.click(screen.getByRole("link", { name: notice.title }));
    expect(await screen.findByText("Safer surveys")).toBeInTheDocument();
    await waitFor(() =>
      expect(api.acknowledgeNotification).toHaveBeenCalledWith(
        1,
        "read",
        expect.any(AbortSignal),
      ),
    );
    expect(api.fetchNotification).toHaveBeenCalledWith(
      1,
      "en",
      expect.any(AbortSignal),
    );
    fireEvent.click(bell());
    expect(await screen.findByText("Read")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: notice.title }),
    ).toBeInTheDocument();
  });

  it("shows read failure and allows retry without discarding content", async () => {
    vi.mocked(api.acknowledgeNotification).mockRejectedValueOnce(
      new Error("offline"),
    );
    setup({ path: "/notifications/1" });
    expect(await screen.findByText("Safer surveys")).toBeInTheDocument();
    fireEvent.click(
      await screen.findByRole("button", { name: "Try marking as read again" }),
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Try marking as read again" }),
      ).not.toBeInTheDocument(),
    );
    expect(api.acknowledgeNotification).toHaveBeenCalledTimes(2);
  });

  it("keeps a notification after failed dismiss and removes it after retry", async () => {
    vi.mocked(api.acknowledgeNotification).mockRejectedValueOnce(
      new Error("offline"),
    );
    setup();
    await screen.findByRole("button", { name: "Notifications: 1 unread" });
    fireEvent.click(bell());
    fireEvent.click(
      screen.getByRole("button", { name: `Dismiss ${notice.title}` }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "could not be saved",
    );
    expect(
      screen.getByRole("link", { name: notice.title }),
    ).toBeInTheDocument();
    vi.mocked(api.acknowledgeNotification).mockResolvedValueOnce({
      ...read,
      dismissed: true,
      state: "dismissed",
    });
    fireEvent.click(
      screen.getByRole("button", { name: `Dismiss ${notice.title}` }),
    );
    expect(
      await screen.findByText(
        "You're all caught up. No notifications to show.",
      ),
    ).toBeInTheDocument();
  });

  it("provides a recoverable loading error", async () => {
    vi.mocked(api.fetchNotifications)
      .mockRejectedValueOnce(new Error("offline"))
      .mockRejectedValueOnce(new Error("offline"));
    setup();
    await waitFor(() =>
      expect(api.fetchNotifications).toHaveBeenCalledTimes(1),
    );
    fireEvent.click(bell());
    expect(
      await screen.findByText(
        "Notifications could not be loaded. Please try again.",
      ),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("status")).not.toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("link", { name: notice.title }),
    ).toBeInTheDocument();
  });

  it("shows loading while the first request is pending", async () => {
    vi.mocked(api.fetchNotifications).mockReturnValueOnce(
      new Promise(() => {}),
    );
    setup();
    fireEvent.click(bell());
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading notifications",
    );
    expect(api.fetchNotifications).toHaveBeenCalledTimes(1);
  });

  it("links to the full feed and release notes without marking the feed read", async () => {
    setup();
    await screen.findByRole("button", { name: "Notifications: 1 unread" });
    fireEvent.click(bell());
    fireEvent.click(
      screen.getByRole("link", { name: "View all notifications" }),
    );
    expect(await screen.findByRole("main")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: notice.title }),
    ).toBeInTheDocument();
    expect(api.acknowledgeNotification).not.toHaveBeenCalled();
  });

  it("renders localized release content without writing notification state", async () => {
    vi.mocked(api.fetchRelease).mockResolvedValueOnce({
      ...release,
      language: "fr",
      title: "Version française",
    });
    setup({ path: "/releases/latest" });
    expect(
      await screen.findByRole("heading", { name: "Version française" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Release improvements").closest("article"),
    ).toHaveAttribute("lang", "fr");
    expect(api.fetchRelease).toHaveBeenCalledWith(
      "latest",
      "en",
      expect.any(AbortSignal),
    );
    expect(api.acknowledgeNotification).not.toHaveBeenCalled();
  });

  it("handles unavailable details and retries", async () => {
    vi.mocked(api.fetchNotification).mockRejectedValueOnce(
      new Error("not found"),
    );
    setup({ path: "/notifications/1" });
    expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
    expect(api.acknowledgeNotification).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Safer surveys")).toBeInTheDocument();
  });
});
