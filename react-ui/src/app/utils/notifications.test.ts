import { beforeEach, describe, expect, it, vi } from "vitest";
import { API } from ".";
import {
  acknowledgeNotification,
  fetchNotification,
  fetchNotifications,
  fetchRelease,
  formatNotificationDate,
} from "./notifications";

vi.mock(".", () => ({ API: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(API.get).mockResolvedValue({ data: [] });
  vi.mocked(API.post).mockResolvedValue({ data: { state: "read" } });
});

describe("notification API helpers", () => {
  it("sends the explicit language, ID, and cancellation signal", async () => {
    const signal = new AbortController().signal;
    await fetchNotifications("fr", signal);
    await fetchNotification(7, "fr", signal);
    await fetchRelease("latest", "fr", signal);
    await fetchRelease(8, "fr", signal);
    expect(API.get).toHaveBeenNthCalledWith(1, "/notifications/", {
      params: { lang: "fr" },
      signal,
    });
    expect(API.get).toHaveBeenNthCalledWith(2, "/notifications/7/", {
      params: { lang: "fr" },
      signal,
    });
    expect(API.get).toHaveBeenNthCalledWith(3, "/releases/latest/", {
      params: { lang: "fr" },
      signal,
    });
    expect(API.get).toHaveBeenNthCalledWith(4, "/releases/8/", {
      params: { lang: "fr" },
      signal,
    });
  });

  it("reads the current CSRF cookie for every write and never posts a user ID", async () => {
    const signal = new AbortController().signal;
    document.cookie = "csrftoken=first; path=/";
    await acknowledgeNotification(7, "read", signal);
    document.cookie = "csrftoken=second; path=/";
    await acknowledgeNotification(7, "dismiss", signal);
    expect(API.post).toHaveBeenNthCalledWith(
      1,
      "/notifications/7/acknowledge/",
      { action: "read" },
      { signal, headers: { "X-CSRFToken": "first" } },
    );
    expect(API.post).toHaveBeenNthCalledWith(
      2,
      "/notifications/7/acknowledge/",
      { action: "dismiss" },
      { signal, headers: { "X-CSRFToken": "second" } },
    );
    document.cookie = "csrftoken=; max-age=0; path=/";
  });

  it("formats a local, localized date and tolerates invalid values/locales", () => {
    expect(formatNotificationDate("invalid", "en")).toBe("");
    const date = "2026-11-03T12:00:00Z";
    expect(formatNotificationDate(date, "fr")).toContain("nov.");
    expect(formatNotificationDate(date, "!invalid")).toContain("Nov");
  });
});
