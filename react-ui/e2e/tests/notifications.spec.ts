import { expect, test, Page } from "@playwright/test";

test.use({ timezoneId: "Europe/Berlin" });

const notice = {
  id: 1,
  release_id: 10,
  language: "en",
  title: "Survey validation improved",
  abstract: "More useful validation messages before publication.",
  publish_at: "2026-11-03T12:00:00Z",
  expires_at: null,
  is_read: false,
};

// Exercise the real app/router/design-system UI against the consumer API contract.
// Backend authorization, CSRF, lifecycle, and storage are tested in Django.
async function consumerAPI(page: Page, signedIn = true) {
  let items = [{ ...notice }];
  const acknowledgements: {
    id: number;
    action: string;
    csrf: string | undefined;
  }[] = [];
  let listRequests = 0;
  let failLists = false;
  let failWrites = false;
  await page.addInitScript(() => {
    localStorage.setItem("i18nextLng", "en");
    localStorage.setItem(
      "cookie-consent.v1",
      JSON.stringify({ essential: true, analytics: false }),
    );
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const headers = {
      "access-control-allow-origin": new URL(page.url()).origin,
      "access-control-allow-credentials": "true",
      "access-control-allow-headers":
        "content-type,x-csrftoken,accept-language",
      "access-control-allow-methods": "GET,POST,OPTIONS",
    };
    const respond = (json: unknown, status = 200) =>
      route.fulfill({ status, json, headers });
    if (request.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers });
    if (pathname === "/api/accounts/user/")
      return respond(
        signedIn
          ? {
              email: "reader@example.org",
              display_name: "Survey Designer",
              sites: [],
              can_access_cms: false,
              read_only_member: false,
            }
          : { detail: "Not authenticated" },
        signedIn ? 200 : 403,
      );
    if (pathname === "/api/notifications/") {
      listRequests += 1;
      return respond(
        failLists ? { detail: "Temporarily unavailable" } : items,
        failLists ? 503 : 200,
      );
    }
    const action = pathname.match(
      /^\/api\/notifications\/(\d+)\/acknowledge\/$/,
    );
    if (action) {
      if (failWrites) return respond({ detail: "Try again" }, 503);
      const id = Number(action[1]);
      const { action: operation } = request.postDataJSON();
      acknowledgements.push({
        id,
        action: operation,
        csrf: request.headers()["x-csrftoken"],
      });
      items =
        operation === "dismiss"
          ? items.filter((item) => item.id !== id)
          : items.map((item) =>
              item.id === id ? { ...item, is_read: true } : item,
            );
      return respond({
        id,
        state: operation === "dismiss" ? "dismissed" : "read",
        dismissed: operation === "dismiss",
        read_at: "2026-11-03T12:05:00Z",
      });
    }
    const detail = pathname.match(/^\/api\/notifications\/(\d+)\/$/);
    if (detail)
      return respond({
        ...(items.find((item) => item.id === Number(detail[1])) || notice),
        body: "<p>Improved <strong>validation</strong> for your surveys.</p>",
      });
    if (pathname.startsWith("/api/releases/"))
      return respond({
        id: 10,
        business_version: "2.1.0",
        title: "Survey Designer 2.1.0",
        body: "<p>Release notes remain available after dismissal.</p>",
        language: "en",
        released_at: notice.publish_at,
        published_at: notice.publish_at,
      });
    return respond([]);
  });
  return {
    acknowledgements,
    get listRequests() {
      return listRequests;
    },
    addNotification() {
      items = [{ ...notice, id: 2, title: "Another update" }, ...items];
    },
    failLists(value: boolean) {
      failLists = value;
    },
    failWrites(value: boolean) {
      failWrites = value;
    },
  };
}

test("notifications retain read items, dismiss only the selected item, and keep release notes", async ({
  page,
  context,
  baseURL,
}, testInfo) => {
  const api = await consumerAPI(page);
  await context.addCookies([
    { name: "csrftoken", value: "browser-test-token", url: baseURL! },
  ]);
  await page.clock.install();
  await page.goto("/notifications");
  const bell = page.getByRole("button", { name: "Notifications: 1 unread" });
  await expect(bell).toBeVisible();
  await bell.click();
  const panel = page.getByRole("region", { name: "Notifications" });
  await expect(panel).toBeVisible();
  await expect(panel.locator("time").first()).toContainText("1:00 PM");
  expect(api.acknowledgements).toHaveLength(0);
  api.addNotification();
  await page.clock.fastForward(300_001);
  await expect(
    panel.getByRole("link", { name: "Another update" }),
  ).toBeVisible();
  expect(api.acknowledgements).toHaveLength(0);
  await page.screenshot({
    path: testInfo.outputPath("notification-panel-desktop.png"),
  });
  await panel.getByRole("link", { name: notice.title }).click();
  await expect(page.getByRole("article")).toContainText("Improved validation");
  await expect
    .poll(() => api.acknowledgements)
    .toEqual([{ id: 1, action: "read", csrf: "browser-test-token" }]);
  await page.getByRole("button", { name: "Notifications: 1 unread" }).click();
  await expect(panel.getByText("Read", { exact: true })).toBeVisible();
  await expect(panel.getByRole("link", { name: notice.title })).toBeVisible();
  await panel.getByRole("button", { name: `Dismiss ${notice.title}` }).click();
  await expect(panel.getByRole("link", { name: notice.title })).toHaveCount(0);
  await expect(
    panel.getByRole("link", { name: "Another update" }),
  ).toBeVisible();
  await panel.getByRole("link", { name: "Latest release" }).click();
  await expect(page.getByRole("article")).toContainText(
    "remain available after dismissal",
  );
});

test("notification failures remain recoverable", async ({ page }) => {
  const api = await consumerAPI(page);
  api.failLists(true);
  await page.goto("/notifications");
  await expect(page.getByRole("alert")).toContainText("could not be loaded");
  api.failLists(false);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("link", { name: notice.title })).toBeVisible();
  api.failWrites(true);
  await page.getByRole("button", { name: `Dismiss ${notice.title}` }).click();
  await expect(page.getByRole("alert")).toContainText("could not be saved");
  await expect(page.getByRole("link", { name: notice.title })).toBeVisible();
  api.failWrites(false);
  await page.getByRole("button", { name: `Dismiss ${notice.title}` }).click();
  await expect(
    page.getByText("You're all caught up. No notifications to show."),
  ).toBeVisible();
});

test("mobile panel supports keyboard opening and Escape", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await consumerAPI(page);
  await page.goto("/notifications");
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  const bell = page.getByRole("button", { name: "Notifications: 1 unread" });
  await bell.focus();
  await bell.press("Enter");
  const panel = page.getByRole("region", { name: "Notifications" });
  await expect(panel).toBeVisible();
  const box = await panel.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: testInfo.outputPath("notification-panel-mobile.png"),
  });
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(bell).toBeFocused();
});

test("signed-out users never request notifications", async ({ page }) => {
  const api = await consumerAPI(page, false);
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Notifications/ })).toHaveCount(
    0,
  );
  expect(api.listRequests).toBe(0);
});
