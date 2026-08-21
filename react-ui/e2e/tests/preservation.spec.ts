import { expect, test, type Page } from "@playwright/test";
import { loginViaDjangoSession } from "../support/auth";
import { apiURL, createPrerequisiteSavedSurvey } from "../support/api";
import {
  advanceFromStepOneToReview,
  goNext,
  waitForReviewReady,
  openSavedSurveyForEdit,
  uniqueSurveyName,
} from "../support/wizard";

async function apiGet(page: Page, path: string, headers: Record<string, string> = {}) {
  const response = await page.request.get(`${apiURL}/api${path}`, { headers });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response;
}

async function apiPost(
  page: Page,
  path: string,
  data: Record<string, unknown>,
  headers: Record<string, string> = {},
) {
  const csrf = (await page.context().cookies(apiURL)).find(
    (cookie) => cookie.name === "csrftoken",
  )?.value;
  const response = await page.request.post(`${apiURL}/api${path}`, {
    data,
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
      ...headers,
    },
  });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response;
}

function questionCount(submodules: any[], selectedSubquestionIds: number[]) {
  const rootCount = submodules.flatMap((submodule) => submodule.root_questions).length;
  const missedSubquestionCount = submodules.flatMap((submodule) =>
    submodule.root_questions.flatMap((root: any) =>
      root.sub_questions.filter((sub: any) => sub.suffix?.name === "_oth"),
    ),
  ).length;
  return rootCount + missedSubquestionCount + selectedSubquestionIds.length;
}

function hasVisibleSubquestion(submodule: any) {
  return submodule.root_questions?.some((root: any) =>
    root.sub_questions?.some((sub: any) => sub.suffix?.name !== "_oth"),
  );
}

async function moveDraggableUp(page: Page, draggedTestId: string) {
  const dragged = page.getByTestId(draggedTestId);
  await dragged.scrollIntoViewIfNeeded();
  await expect(dragged).toBeVisible();
  await dragged.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowUp");
  await page.keyboard.press("Space");
  await page.keyboard.press("Escape");
}

function getIds(items: any[]) {
  return items.map((item) => item.id);
}

test("saved survey preserves order and subquestion choices through edit/save", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);

  const seed = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Preservation Seed"),
  );
  const orgHeaders = { "Survey-Designer-Organizations": String(seed.organization.id) };

  const modulesResponse = await apiGet(
    page,
    `/modules/?type=${seed.type.id}&mode=${seed.mode.id}&attributes=`,
    orgHeaders,
  );
  const modules = await modulesResponse.json();
  const activeModules = modules.filter((module: any) =>
    module.submodules?.some((submodule: any) => submodule.is_active !== false),
  );
  expect(activeModules.length).toBeGreaterThan(0);

  const candidates = activeModules.flatMap((module: any) =>
    module.submodules
      .filter((submodule: any) => submodule.is_active !== false)
      .map((submodule: any) => ({ module, submodule })),
  );
  const allSubmoduleIds = candidates.map(({ submodule }: any) => submodule.id);
  let chosenSubmodules: any[] | null = null;
  let submoduleDetails: any[] = [];
  let submoduleWithSubquestion: any | undefined;
  for (let firstIndex = 0; firstIndex < candidates.length; firstIndex += 1) {
    for (let secondIndex = firstIndex + 1; secondIndex < candidates.length; secondIndex += 1) {
      const pair = [candidates[firstIndex], candidates[secondIndex]];
      const ids = pair.map(({ submodule }: any) => submodule.id);
      const validationResponse = await apiGet(
        page,
        `/order-validation/?submodule_ids=${ids.join(",")}&indicator_ids=&all_submodule_ids=${allSubmoduleIds.join(",")}`,
        orgHeaders,
      );
      const validationMessages = await validationResponse.json();
      if (validationMessages.length) continue;

      const detailResponse = await apiGet(
        page,
        `/submodules/?submodule_ids=${ids.join(",")}&indicator_ids=`,
        orgHeaders,
      );
      const details = await detailResponse.json();
      const detailWithSubquestion = details.find((submodule: any) =>
        hasVisibleSubquestion(submodule),
      );
      if (detailWithSubquestion) {
        chosenSubmodules = pair;
        submoduleDetails = details;
        submoduleWithSubquestion = detailWithSubquestion;
        break;
      }
    }
    if (chosenSubmodules) break;
  }
  expect(chosenSubmodules, "Expected at least one valid two-submodule fixture combination").toBeTruthy();

  const modulesOrder = [...new Set(chosenSubmodules!.map(({ module }: any) => module.id))].reverse();
  const submodulesOrder = chosenSubmodules!.map(({ submodule }: any) => submodule.id).reverse();
  const selectedSubmoduleIds = chosenSubmodules!.map(({ submodule }: any) => submodule.id);
  expect(submoduleWithSubquestion, "Expected at least one selectable subquestion fixture").toBeTruthy();
  const selectedSubquestion = submoduleWithSubquestion.root_questions
    .flatMap((root: any) => root.sub_questions || [])
    .find((subquestion: any) => subquestion.suffix?.name !== "_oth");
  expect(selectedSubquestion, "Expected at least one visible selectable subquestion").toBeTruthy();

  const surveyName = uniqueSurveyName(testInfo, "E2E Preservation Survey");
  const payload = {
    ...seed.payload,
    name: surveyName,
    modules_order: modulesOrder,
    submodules: selectedSubmoduleIds,
    submodules_order: submodulesOrder,
    subquestions: {
      [submoduleWithSubquestion.id]: [selectedSubquestion.id],
    },
  };

  await apiPost(page, "/saved-surveys/", payload, orgHeaders);
  const savedResponse = await apiGet(
    page,
    `/saved-surveys/?name=${encodeURIComponent(surveyName)}`,
  );
  const savedSurvey = (await savedResponse.json()).find(
    (survey: any) => survey.name === surveyName,
  );
  expect(savedSurvey).toBeTruthy();
  expect(savedSurvey.subquestion_submodule_mapping[submoduleWithSubquestion.id]).toEqual(
    expect.arrayContaining([expect.objectContaining({ id: selectedSubquestion.id })]),
  );

  await page.goto("/design/survey");
  await openSavedSurveyForEdit(page, savedSurvey.uuid);
  await advanceFromStepOneToReview(page);

  const expectedQuestionCount = questionCount(submoduleDetails, [selectedSubquestion.id]);
  const stepHeader = page.locator(".survey-module .wfp--module__header");
  await expect(stepHeader).toContainText(/questions? to be generated/i);
  const headerText = await stepHeader.textContent();
  const actualQuestionCount = Number(headerText?.match(/\((\d+) questions? to be generated\)/i)?.[1]);
  expect(actualQuestionCount, "Step 3 question count should be visible").toBeGreaterThan(0);
  expect(actualQuestionCount).toBe(expectedQuestionCount);

  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(/Step:\s*4/i);
  await page.getByRole("button", { name: /save/i }).click();
  await expect(page.getByRole("alert").filter({ hasText: /survey updated successfully/i })).toBeVisible();

  const roundTripResponse = await apiGet(page, `/saved-surveys/${savedSurvey.uuid}/`);
  const roundTrip = await roundTripResponse.json();
  expect(roundTrip.modules_order).toEqual(modulesOrder);
  expect(roundTrip.submodules_order).toEqual(submodulesOrder);
  const roundTripSubmoduleIds = roundTrip.submodules.map((submodule: any) =>
    typeof submodule === "number" ? submodule : submodule.id,
  );
  expect(roundTripSubmoduleIds.sort()).toEqual([...selectedSubmoduleIds].sort());
  expect(roundTrip.subquestion_submodule_mapping[submoduleWithSubquestion.id]).toEqual(
    expect.arrayContaining([expect.objectContaining({ id: selectedSubquestion.id })]),
  );
});


test("dragging modules and submodules preserves saved order", async ({ page }, testInfo) => {
  await loginViaDjangoSession(page);

  const seed = await createPrerequisiteSavedSurvey(
    page,
    uniqueSurveyName(testInfo, "E2E Drag Seed"),
  );
  const orgHeaders = { "Survey-Designer-Organizations": String(seed.organization.id) };

  const modulesResponse = await apiGet(
    page,
    `/modules/?type=${seed.type.id}&mode=${seed.mode.id}&attributes=`,
    orgHeaders,
  );
  const modules = await modulesResponse.json();
  const activeModules = modules
    .map((module: any) => ({
      ...module,
      submodules: (module.submodules || []).filter(
        (submodule: any) => submodule.is_active !== false,
      ),
    }))
    .filter((module: any) => module.submodules.length);
  const allSubmoduleIds = activeModules.flatMap((module: any) => getIds(module.submodules));

  let moduleA: any | undefined;
  let moduleB: any | undefined;
  let moduleASubmodules: any[] = [];
  let moduleBSubmodule: any | undefined;

  for (const firstModule of activeModules.filter((module: any) => module.submodules.length >= 2)) {
    for (let firstIndex = 0; firstIndex < firstModule.submodules.length - 1; firstIndex += 1) {
      const firstPair = [firstModule.submodules[firstIndex], firstModule.submodules[firstIndex + 1]];
      for (const secondModule of activeModules.filter((module: any) => module.id !== firstModule.id)) {
        for (const secondSubmodule of secondModule.submodules) {
          const finalOrder = [secondSubmodule.id, firstPair[1].id, firstPair[0].id];
          const validationResponse = await apiGet(
            page,
            `/order-validation/?submodule_ids=${finalOrder.join(",")}&indicator_ids=&all_submodule_ids=${allSubmoduleIds.join(",")}`,
            orgHeaders,
          );
          const validationMessages = await validationResponse.json();
          if (!validationMessages.length) {
            moduleA = firstModule;
            moduleB = secondModule;
            moduleASubmodules = firstPair;
            moduleBSubmodule = secondSubmodule;
            break;
          }
        }
        if (moduleA) break;
      }
      if (moduleA) break;
    }
    if (moduleA) break;
  }

  expect(moduleA, "Expected fixtures with draggable module/submodule combination").toBeTruthy();
  expect(moduleB).toBeTruthy();
  expect(moduleBSubmodule).toBeTruthy();

  const surveyName = uniqueSurveyName(testInfo, "E2E Drag Survey");
  const initialSubmoduleOrder = [
    moduleASubmodules[0].id,
    moduleASubmodules[1].id,
    moduleBSubmodule.id,
  ];
  const expectedModulesOrder = [moduleB!.id, moduleA!.id];
  const expectedSubmodulesOrder = [
    moduleBSubmodule.id,
    moduleASubmodules[1].id,
    moduleASubmodules[0].id,
  ];
  const payload = {
    ...seed.payload,
    name: surveyName,
    modules_order: [moduleA!.id, moduleB!.id],
    submodules: initialSubmoduleOrder,
    submodules_order: initialSubmoduleOrder,
  };

  await apiPost(page, "/saved-surveys/", payload, orgHeaders);
  const savedResponse = await apiGet(
    page,
    `/saved-surveys/?name=${encodeURIComponent(surveyName)}`,
  );
  const savedSurvey = (await savedResponse.json()).find(
    (survey: any) => survey.name === surveyName,
  );
  expect(savedSurvey).toBeTruthy();

  await page.goto("/design/survey");
  await openSavedSurveyForEdit(page, savedSurvey.uuid);
  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*2/i,
  );

  await moveDraggableUp(page, `module-draggable-${moduleB!.id}`);
  await expect(page.getByTestId(`module-draggable-${moduleB!.id}`)).toBeVisible();

  await moveDraggableUp(page, `submodule-draggable-${moduleASubmodules[1].id}`);
  await expect(
    page.getByTestId(`submodule-draggable-${moduleASubmodules[1].id}`),
  ).toBeVisible();

  await goNext(page);
  await expect(page.locator(".survey-module .wfp--module__header")).toContainText(
    /Step:\s*3/i,
  );
  await waitForReviewReady(page);
  await goNext(page);
  const saveButton = page.getByRole("button", { name: /save/i });
  await expect(saveButton).toBeVisible();
  await expect(saveButton).toBeEnabled();
  await saveButton.click({ force: true });
  await expect(page.getByRole("alert").filter({ hasText: /survey updated successfully/i })).toBeVisible();

  const roundTripResponse = await apiGet(page, `/saved-surveys/${savedSurvey.uuid}/`);
  const roundTrip = await roundTripResponse.json();
  expect(roundTrip.modules_order).toEqual(expectedModulesOrder);
  expect(roundTrip.submodules_order).toEqual(expectedSubmodulesOrder);
});
