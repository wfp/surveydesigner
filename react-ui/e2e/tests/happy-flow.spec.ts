import { expect, test } from "@playwright/test";
import { stat } from "node:fs/promises";
import { loginViaDjangoSession } from "../support/auth";
import { createPrerequisiteSavedSurvey } from "../support/api";
import {
  advanceFromStepOneToGenerate,
  advanceFromStepOneToReview,
  completeSurveyWizard,
  expectSavedSurveyVisible,
  goToSavedSurveys,
  openSavedSurveyForEdit,
  uniqueSurveyName,
} from "../support/wizard";

test("user can create and save a survey through the wizard", async ({ page }, testInfo) => {
  const surveyName = uniqueSurveyName(testInfo);

  await loginViaDjangoSession(page);
  await page.goto("/design/survey");

  await completeSurveyWizard(page, surveyName);
  await page.getByRole("button", { name: /save/i }).click();

  await expect(page.getByRole("alert").filter({ hasText: /survey saved successfully/i })).toBeVisible();
  await expectSavedSurveyVisible(page, surveyName);
});

test("user can edit a saved survey and persist the updated name", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);
  const savedSurvey = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Edit Source"),
  );
  const updatedName = uniqueSurveyName(testInfo, "E2E Edited Survey");

  await page.goto("/design/survey");
  await openSavedSurveyForEdit(page, savedSurvey.uuid);
  await page.locator("#id_name_input").fill(updatedName);
  await advanceFromStepOneToGenerate(page);
  await page.getByRole("button", { name: /save/i }).click();

  await expect(page.getByRole("alert").filter({ hasText: /survey updated successfully/i })).toBeVisible();
  await expectSavedSurveyVisible(page, updatedName);
});

test("user can share a saved survey link and import a copy", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);
  const savedSurvey = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Share Source"),
  );

  await page.goto("/design/survey");
  await goToSavedSurveys(page);
  await page.getByTestId(`saved-survey-share-${savedSurvey.uuid}`).click();

  const expectedShareURL = new RegExp(`/survey/copy/${savedSurvey.uuid}$`);
  const shareInput = page.getByTestId("share-survey-link");
  await expect(shareInput).toHaveValue(expectedShareURL);

  const copyResponse = await page.request.get(
    `${process.env.E2E_API_URL ?? "http://localhost:8080"}/api/saved-surveys/${savedSurvey.uuid}/copy/`,
  );
  expect(copyResponse.ok(), await copyResponse.text()).toBeTruthy();
  const copiedSurvey = await copyResponse.json();
  expect(copiedSurvey.uuid).toBeTruthy();

  await page.reload();
  await goToSavedSurveys(page);
  await expect(page.getByTestId(`saved-survey-edit-${copiedSurvey.uuid}`)).toBeVisible();
});

test("user can preview a valid survey from the review step", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);
  const savedSurvey = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Preview Source"),
  );

  await page.goto("/design/survey");
  await openSavedSurveyForEdit(page, savedSurvey.uuid);
  await advanceFromStepOneToReview(page);

  const previewResponse = page.waitForResponse(
    (response) => response.url().includes("/api/preview/") && response.status() === 200,
  );
  await page.getByRole("button", { name: /preview survey/i }).click();
  await previewResponse;

  await expect(page.locator('[role="preview_errors"]')).toHaveCount(0);
  await expect(page.locator('[role="api_errors"]')).toHaveCount(0);
});

test("user can export XLSX and start DOCX generation from the generate step", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);
  const savedSurvey = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Export Source"),
  );

  await page.goto("/design/survey");
  await openSavedSurveyForEdit(page, savedSurvey.uuid);
  await advanceFromStepOneToGenerate(page);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("download-xlsx").click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.(xlsx|zip)$/);
  const downloadPath = await download.path();
  expect(downloadPath, "XLSX download path should be available").toBeTruthy();
  const fileStats = await stat(downloadPath as string);
  expect(fileStats.size).toBeGreaterThan(0);

  const docResponse = page.waitForResponse(
    (response) => response.url().includes("/api/generate-doc/") && response.request().method() === "POST",
  );
  await page.getByTestId("download-docx").click();
  expect((await docResponse).ok()).toBeTruthy();
});
