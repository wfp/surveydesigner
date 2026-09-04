import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

export function uniqueSurveyName(testInfo: TestInfo, prefix = "E2E Survey") {
  return `${prefix} ${Date.now()}-${testInfo.parallelIndex}-${testInfo.retry}`;
}

export async function selectReactSelectOption(
  page: Page,
  selectId: string,
  optionName?: string | RegExp,
) {
  const input = page.locator(`#${selectId}`);
  await expect(input).toBeVisible();
  await input.click();

  if (typeof optionName === "string") {
    await page.keyboard.type(optionName);
  }

  const menu = page.locator(".wfp--react-select__menu").last();
  await expect(menu).toBeVisible();

  let option: Locator;
  if (optionName instanceof RegExp) {
    option = menu.getByText(optionName).first();
  } else if (typeof optionName === "string") {
    option = menu.getByText(optionName, { exact: false }).first();
  } else {
    option = menu.locator(".wfp--react-select__option").first();
  }

  await expect(option).toBeVisible();
  await option.click();
}

export async function dismissBlockingChrome(page: Page) {
  const hasStoredConsent = await page.evaluate(
    () => window.localStorage.getItem("cookie-consent.v1") !== null,
  );
  if (!hasStoredConsent) {
    await page
      .getByRole("button", { name: /reject analytics/i })
      .click({ timeout: 5_000 })
      .catch(() => {});
  }

  const snoozeMaintenance = page.getByRole("button", { name: /snooze for 1 day/i });
  if (await snoozeMaintenance.isVisible().catch(() => false)) {
    await snoozeMaintenance.click();
  }
}

export async function goNext(page: Page) {
  await dismissBlockingChrome(page);
  await page.getByRole("button", { name: /next/i }).click();
}

async function waitForModuleSelection(page: Page) {
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /submodules selected/i,
  );
}

export async function waitForReviewReady(page: Page) {
  await expect(page.locator("#id_language_select")).toBeVisible({ timeout: 30_000 });
}
async function deselectSubmodule(page: Page, item: Locator) {
  const checkbox = item.locator('input[type="checkbox"]');
  if (!(await checkbox.isChecked())) return;

  await item.locator("label").click();
  const modal = page.locator(".wfp--modal.is-visible");
  const confirmButton = modal.getByRole("button", { name: "Yes", exact: true });
  await expect(confirmButton).toBeVisible();
  await confirmButton.click();
  await expect(modal).toHaveCount(0);
}

async function selectCompactSubmodule(page: Page) {
  // Mandatory defaults are configuration-driven; retain the first available one.
  const allItems = page.locator(".submodule-item");
  await expect(allItems.first().locator("label")).toBeVisible();

  let selectedItems = page.locator(
    '.submodule-item:has(input[type="checkbox"]:checked)',
  );
  if ((await selectedItems.count()) === 0) {
    await allItems.first().locator("label").click();
    selectedItems = page.locator(
      '.submodule-item:has(input[type="checkbox"]:checked)',
    );
  }

  const keepItem = selectedItems.first();
  await expect(keepItem.locator("label")).toBeVisible();

  while ((await selectedItems.count()) > 1) {
    await deselectSubmodule(page, selectedItems.last());
  }

  await expect(keepItem.locator('input[type="checkbox"]')).toBeChecked();
}

export async function goToSavedSurveys(page: Page) {
  await dismissBlockingChrome(page);
  const table = page.getByTestId("saved-surveys-table");
  if (await table.isVisible().catch(() => false)) return;

  const savedSurveysButton = page.getByRole("button", { name: /saved surveys/i });
  await expect(savedSurveysButton.or(table).first()).toBeVisible();

  if (await table.isVisible().catch(() => false)) return;

  await savedSurveysButton.click();
  await expect(table).toBeVisible();
}

export function savedSurveyRow(page: Page, name: string) {
  return page.getByTestId("saved-surveys-table").locator("tr", { hasText: name });
}

export async function expectSavedSurveyVisible(page: Page, name: string) {
  await goToSavedSurveys(page);
  await expect(savedSurveyRow(page, name)).toBeVisible();
}

export async function fillStepOne(page: Page, name: string) {
  await dismissBlockingChrome(page);
  await page.locator("#id_name_input").fill(name);
  await selectReactSelectOption(page, "id_organizations_select");
  await page.keyboard.press("Escape");
  await selectReactSelectOption(page, "id_category_select", /monitoring/i);
  await selectReactSelectOption(
    page,
    "id_types_select",
    /post-distribution monitoring|pdm/i,
  );
  await selectReactSelectOption(page, "id_mode_select", /face[- ]?to[- ]?face/i);
}

export async function completeSurveyWizard(page: Page, name: string) {
  await fillStepOne(page, name);
  await goNext(page);

  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*2/i,
  );
  await selectCompactSubmodule(page);
  await goNext(page);

  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*3/i,
  );
  await waitForReviewReady(page);
  await goNext(page);

  await expect(page.getByRole("button", { name: /save/i })).toBeVisible();
}

export async function openSavedSurveyForEdit(page: Page, uuid: string) {
  await goToSavedSurveys(page);
  await page.getByTestId(`saved-survey-edit-${uuid}`).click();
  await expect(page.locator("#id_name_input")).toBeVisible();
}

export async function advanceFromStepOneToGenerate(page: Page) {
  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*2/i,
  );
  await expect(page.locator("#id-submodule-select-all")).toBeAttached();
  await waitForModuleSelection(page);
  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*3/i,
  );
  await waitForReviewReady(page);
  await goNext(page);
  await expect(page.getByRole("button", { name: /save/i })).toBeVisible();
}

export async function advanceFromStepOneToReview(page: Page) {
  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*2/i,
  );
  await expect(page.locator("#id-submodule-select-all")).toBeAttached();
  await waitForModuleSelection(page);
  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*3/i,
  );
  await waitForReviewReady(page);
}
