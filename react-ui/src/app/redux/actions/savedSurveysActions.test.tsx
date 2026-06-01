import { describe, expect, it, vi, beforeEach, Mock } from "vitest";

import { API } from "../../utils";
import { SurveyFormState } from "../reducers/surveyFormReducer";
import { createTestStore } from "../store";
import { postSavedSurvey, putSavedSurvey } from "./savedSurveysActions";

vi.mock("../../utils", () => ({
  API: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

function deferredResponse<T>(data: T) {
  let resolve: (value: { data: T }) => void = () => {};
  const promise = new Promise<{ data: T }>((res) => {
    resolve = res;
  });

  return {
    promise,
    resolve: () => resolve({ data }),
  };
}

const survey: SurveyFormState = {
  name: "Ordered survey",
  organizations: [{ id: 1, value: 1, label: "Org" }],
  category: null,
  type: null,
  mode: null,
  attributes: [],
  modules_order: [3, 1, 2],
  submodules: [30, 10, 20],
  indicators: [],
  indicator_areas_order: [],
  indicators_order: {},
  sub_questions: [],
  languages: [{ language: "en", language_display: "English" }],
  submodules_order: [30, 10, 20],
} as SurveyFormState;

describe("saved survey actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("keeps create pending until the saved survey request completes", async () => {
    const response = deferredResponse({ message: "saved" });
    (API.post as Mock).mockReturnValue(response.promise);

    const store = createTestStore();
    let settled = false;

    const actionPromise = store.dispatch(postSavedSurvey(survey)).then((action) => {
      settled = true;
      return action;
    });

    await Promise.resolve();
    expect(settled).toBe(false);

    response.resolve();

    await expect(actionPromise).resolves.toMatchObject({
      payload: { message: "saved" },
      type: "saved_surveys/POST_SAVEDSURVEYS/fulfilled",
    });
  });

  it("keeps update pending until the saved survey request completes", async () => {
    const response = deferredResponse({ message: "updated" });
    (API.put as Mock).mockReturnValue(response.promise);

    const store = createTestStore();
    let settled = false;

    const actionPromise = store
      .dispatch(putSavedSurvey({ ...survey, uuid: "saved-survey-uuid" }))
      .then((action) => {
        settled = true;
        return action;
      });

    await Promise.resolve();
    expect(settled).toBe(false);

    response.resolve();

    await expect(actionPromise).resolves.toMatchObject({
      payload: { message: "updated" },
      type: "saved_surveys/PUT_SAVEDSURVEYS/fulfilled",
    });
  });
});
