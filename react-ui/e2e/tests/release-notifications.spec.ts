import { expect, test, type Page } from "@playwright/test";

const original = {
  id: 1,
  version: "12.9.3",
  description:
    "Improved survey validation.\nAdded external choice-file checks.",
  deployed_at: "2026-10-06T10:30:00Z",
  state: "unread",
};

async function mockAuthenticatedPage(page: Page, many = false) {
  await page.addInitScript(() => localStorage.setItem("i18nextLng", "en"));
  await page.route("**/api/accounts/user/", (route) =>
    route.fulfill({
      json: {
        email: "notification-test@example.com",
        display_name: "Notification test",
        can_access_cms: false,
        read_only_member: false,
        sites: [],
      },
    }),
  );
  await page.route("**/api/frontend-content/", (route) =>
    route.fulfill({ json: [] }),
  );
  let events = [
    { ...original },
    {
      ...original,
      id: 2,
      version: "12.9.2",
      state: "read",
      description: "Previously released improvements.",
    },
  ];
  if (many)
    events.push(
      ...Array.from({ length: 23 }, (_, i) => ({
        ...original,
        id: i + 3,
        version: "OLDER-" + i,
        state: "read",
      })),
    );
  const calls: string[] = [];
  await page.route("**/api/release-notifications/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    calls.push(path);
    if (path.endsWith("/read/")) {
      const id = Number(path.split("/")[3]);
      events = events.map((item) =>
        item.id === id ? { ...item, state: "read" } : item,
      );
      await route.fulfill({
        json: { release: events.find((item) => item.id === id) },
      });
    } else if (path.endsWith("/clear/")) {
      const { release_ids: ids } = route.request().postDataJSON();
      events = events.map((item) =>
        ids.includes(item.id) ? { ...item, state: "cleared" } : item,
      );
      await route.fulfill({ json: { cleared_ids: ids } });
    } else {
      const unread_count = events.filter(
        (item) => item.state === "unread",
      ).length;
      const pageNumber = Number(url.searchParams.get("page") || 1);
      await route.fulfill({
        json: {
          results: path.endsWith("/recent/")
            ? events.slice(0, 5).filter((item) => item.state !== "cleared")
            : events.slice((pageNumber - 1) * 20, pageNumber * 20),
          unread_count,
          count: events.length,
        },
      });
    }
  });
  return {
    calls,
    deploy: () => {
      events.unshift({ ...original, id: 99, version: "12.9.4" });
    },
  };
}

test("read and unread releases stay visible, with full history after clearing", async ({
  page,
}) => {
  const backend = await mockAuthenticatedPage(page);
  await page.goto("/");
  const bell = page.getByRole("button", {
    name: "Latest changes, unread release",
  });
  await bell.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Latest changes" });
  await expect(dialog.getByText("New", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Read", { exact: true })).toBeVisible();
  expect(backend.calls.some((path) => path.endsWith("/read/"))).toBe(false);
  await dialog.getByRole("button", { name: "Version 12.9.3" }).click();
  await expect(dialog.getByText("Read", { exact: true })).toHaveCount(2);
  await expect(
    dialog.getByRole("button", { name: "Version 12.9.3" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/release-notifications-desktop.png",
  });
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Latest changes", exact: true }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Latest changes", exact: true })
    .click();
  await dialog.getByRole("button", { name: "Clear notifications" }).click();
  await expect(dialog).toContainText("No new release notifications.");
  await dialog.getByRole("link", { name: "View all notifications" }).click();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(
    page.getByRole("heading", { name: "Release notifications", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Version 12.9.3" }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Version 12.9.2" }).first(),
  ).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(
    page.getByRole("heading", { name: "Release notifications", exact: true }),
  ).toBeVisible();
});

test("new event stays unread until clicked and mobile layout fits", async ({
  page,
}) => {
  const backend = await mockAuthenticatedPage(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Reject analytics" }).click();
  await page
    .getByRole("button", { name: "Latest changes, unread release" })
    .click();
  await page.getByRole("button", { name: "Version 12.9.3" }).click();
  await expect(page.getByTestId("release-unread-marker")).toHaveCount(0);
  backend.deploy();
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByTestId("release-unread-marker")).toBeVisible();
  expect(backend.calls.some((path) => path.includes("/99/read/"))).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  const bell = page.getByRole("button", {
    name: "Latest changes, unread release",
  });
  if ((await bell.getAttribute("aria-expanded")) !== "true") await bell.click();
  const dialog = page.getByRole("dialog", { name: "Latest changes" });
  await expect(
    dialog.getByRole("button", { name: "Version 12.9.4" }),
  ).toBeVisible();
  const bounds = await dialog.boundingBox();
  expect(bounds?.x).toBeGreaterThanOrEqual(0);
  expect((bounds?.x || 0) + (bounds?.width || 0)).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "test-results/release-notifications-mobile.png",
  });
  await dialog.getByRole("link", { name: "View all notifications" }).click();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(
    page.getByRole("button", { name: "Version 12.9.4" }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/release-history-mobile.png" });
});

test("history paginates without dropping older records", async ({ page }) => {
  await mockAuthenticatedPage(page, true);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Latest changes, unread release" })
    .click();
  await page.getByRole("link", { name: "View all notifications" }).click();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(
    page.getByRole("button", { name: "Version 12.9.3" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Version OLDER-18" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Version 12.9.3" }),
  ).toHaveCount(0);
});

test("signed-out page never requests notifications", async ({ page }) => {
  let requests = 0;
  await page.route("**/api/accounts/user/", (route) =>
    route.fulfill({ status: 403, json: {} }),
  );
  await page.route("**/api/release-notifications/**", (route) => {
    requests += 1;
    return route.fulfill({ json: { results: [], unread_count: 0 } });
  });
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Log in", exact: true }).first(),
  ).toBeVisible();
  expect(requests).toBe(0);
  await expect(
    page.getByRole("button", { name: /Latest changes/ }),
  ).toHaveCount(0);
});

test("live backend retains read releases and cleared releases in history", async ({
  page,
}) => {
  const session = process.env.E2E_RELEASE_LIVE_SESSIONID;
  test.skip(
    !session,
    "Requires a disposable Django session with an unread release.",
  );
  await page.context().addCookies([
    {
      name: "sessionid",
      value: session as string,
      url: process.env.E2E_API_URL || "http://localhost:8080",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
  await page.addInitScript(() => localStorage.setItem("i18nextLng", "en"));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Latest changes, unread release" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Latest changes" });
  const release = dialog.getByRole("button", { name: /^Version / }).first();
  const releaseName = await release.textContent();
  const readResponse = page.waitForResponse((response) =>
    response.url().endsWith("/read/"),
  );
  await release.click();
  expect((await readResponse).status()).toBe(200);
  await expect(release).toBeVisible();
  const clearResponse = page.waitForResponse((response) =>
    response.url().endsWith("/release-notifications/clear/"),
  );
  await dialog.getByRole("button", { name: "Clear notifications" }).click();
  expect((await clearResponse).status()).toBe(200);
  await dialog.getByRole("link", { name: "View all notifications" }).click();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(
    page.getByRole("button", { name: releaseName || "", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: releaseName || "", exact: true }),
  ).toBeVisible();
});
