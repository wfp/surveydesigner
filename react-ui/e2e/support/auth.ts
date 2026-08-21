import { expect, type Page } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://localhost:8080";
const email = process.env.E2E_USER_EMAIL ?? "admin@wfp.org";
const token = process.env.E2E_AUTH_TOKEN;

export async function loginViaDjangoSession(page: Page) {
  expect(token, "E2E_AUTH_TOKEN must be set for authenticated E2E tests").toBeTruthy();

  const response = await page.request.post(`${apiURL}/auth/e2e-login/`, {
    headers: {
      "X-E2E-Auth-Token": token as string,
    },
    data: { email },
  });

  expect(response.ok(), await response.text()).toBeTruthy();

  const setCookie = response.headers()["set-cookie"] ?? "";
  const sessionId = setCookie.match(/sessionid=([^;]+)/)?.[1];
  const csrfToken = setCookie.match(/csrftoken=([^;]+)/)?.[1];
  expect(sessionId, "Django session cookie was not returned").toBeTruthy();
  expect(csrfToken, "Django CSRF cookie was not returned").toBeTruthy();

  await page.context().addCookies([
    {
      name: "sessionid",
      value: sessionId as string,
      url: apiURL,
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "csrftoken",
      value: csrfToken as string,
      url: apiURL,
      sameSite: "Lax",
    },
  ]);
}
