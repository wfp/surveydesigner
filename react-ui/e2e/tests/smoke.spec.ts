import { expect, test } from "@playwright/test";
import { loginViaDjangoSession } from "../support/auth";

test("anonymous user sees the landing page", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("#landing-page")).toBeVisible();
  await expect(page.getByRole("link", { name: /log in/i }).first()).toBeVisible();
  await expect(page.getByAltText("Survey Designer Screenshot")).toBeVisible();
  await expect(page).toHaveTitle(/Survey Designer/i);
});

test("anonymous user is redirected away from authenticated routes", async ({ page }) => {
  await page.goto("/design/survey");

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("#landing-page")).toBeVisible();
});

test("authenticated user can open the survey designer", async ({ page }) => {
  await loginViaDjangoSession(page);
  await page.goto("/");

  await expect(page).toHaveURL(/\/design\/survey/);
  await expect(page.locator(".survey-wizard")).toBeVisible();
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(/Step:\s*1/i);
  await expect(page.locator("#id_name_input")).toBeVisible();
});
