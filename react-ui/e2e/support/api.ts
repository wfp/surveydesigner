import { expect, type Page } from "@playwright/test";

export const apiURL = process.env.E2E_API_URL ?? "http://localhost:8080";

export interface SurveySeed {
  name: string;
  uuid: string;
  organization: any;
  category: any;
  type: any;
  mode: any;
  module: any;
  submodule: any;
  payload: Record<string, unknown>;
}

async function expectOk(response: any, message: string) {
  expect(response.ok(), `${message}: ${await response.text()}`).toBeTruthy();
  return response;
}

async function apiGet(page: Page, path: string, headers: Record<string, string> = {}) {
  return expectOk(
    await page.request.get(`${apiURL}/api${path}`, { headers }),
    `GET ${path} failed`,
  );
}

async function apiPost(
  page: Page,
  path: string,
  data: Record<string, unknown>,
  headers: Record<string, string> = {},
) {
  const cookies = await page.context().cookies(apiURL);
  const csrf = cookies.find((cookie) => cookie.name === "csrftoken")?.value;

  return expectOk(
    await page.request.post(`${apiURL}/api${path}`, {
      data,
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRFToken": csrf } : {}),
        ...headers,
      },
    }),
    `POST ${path} failed`,
  );
}

function pickByLabel<T extends { label?: string; name?: string; is_active?: boolean }>(
  items: T[],
  preferred: RegExp,
) {
  const activeItems = items.filter((item) => item.is_active !== false);
  return (
    activeItems.find((item) => preferred.test(item.label ?? item.name ?? "")) ??
    activeItems[0] ??
    items[0]
  );
}

export async function createPrerequisiteSavedSurvey(
  page: Page,
  name: string,
): Promise<SurveySeed> {
  const organizationsResponse = await apiGet(page, "/organizations/");
  const organizations = await organizationsResponse.json();
  const organization = pickByLabel(organizations, /world food programme|\bwfp\b/i);
  expect(organization, "No organization is available for E2E setup").toBeTruthy();

  const orgHeaders = { "Survey-Designer-Organizations": String(organization.id) };
  const surveysResponse = await apiGet(page, "/surveys/", orgHeaders);
  const surveys = await surveysResponse.json();
  const categories = surveys.categories.filter(
    (category: any) => category.survey_types?.length,
  );
  const category = pickByLabel(categories, /monitoring/i);
  expect(category, "No survey category with types is available").toBeTruthy();

  const type = pickByLabel(
    category.survey_types ?? [],
    /post-distribution monitoring|pdm/i,
  );
  expect(type, "No survey type is available").toBeTruthy();

  const mode = pickByLabel(surveys.modes ?? [], /face[- ]?to[- ]?face/i);
  expect(mode, "No survey mode is available").toBeTruthy();

  const modulesResponse = await apiGet(
    page,
    `/modules/?type=${type.id}&mode=${mode.id}&attributes=`,
    orgHeaders,
  );
  const modules = await modulesResponse.json();
  const candidates = modules.flatMap((candidateModule: any) =>
    (candidateModule.submodules ?? [])
      .filter(
        (submodule: any) =>
          submodule.is_active !== false && submodule.root_questions?.length,
      )
      .map((submodule: any) => ({ module: candidateModule, submodule })),
  );
  expect(candidates.length, "No question-backed submodules are available").toBeGreaterThan(0);

  let validCandidate = candidates[0];
  for (const candidate of candidates.slice(0, 12)) {
    const previewPayload = {
      name: `${name} Preview Probe`,
      survey_type: type.id,
      submodules: [candidate.submodule.id],
      submodules_order: [candidate.submodule.id],
      sub_questions: [],
      languages: ["en"],
      indicators: [],
    };
    const previewResponse = await apiPost(
      page,
      "/preview/",
      previewPayload,
      orgHeaders,
    ).catch(() => null);
    if (!previewResponse) continue;
    const preview = await previewResponse.json();
    if (!preview.errors?.length) {
      validCandidate = candidate;
      break;
    }
  }

  const { module, submodule } = validCandidate;

  const payload = {
    name,
    organizations: [organization.id],
    survey_category: category.id,
    survey_type: type.id,
    survey_mode: mode.id,
    indicators: [],
    modules_order: [module.id],
    submodules: [submodule.id],
    submodules_order: [submodule.id],
    subquestions: {},
    attributes: [],
    indicator_areas_order: [],
    indicators_order: {},
    languages: [{ language: "en", language_display: "English" }],
  };

  await apiPost(page, "/saved-surveys/", payload, orgHeaders);

  const savedResponse = await apiGet(
    page,
    `/saved-surveys/?name=${encodeURIComponent(name)}`,
  );
  const savedSurveys = await savedResponse.json();
  const savedSurvey = savedSurveys.find((survey: any) => survey.name === name);
  expect(savedSurvey, `Saved survey ${name} was not returned by the API`).toBeTruthy();

  return {
    name,
    uuid: savedSurvey.uuid,
    organization,
    category,
    type,
    mode,
    module,
    submodule,
    payload,
  };
}
