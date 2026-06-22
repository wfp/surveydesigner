import { describe, expect, it } from "vitest";

import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";
import {
  clearModuleDependentSurveyData,
  haveModuleCriteriaChanged,
} from "./moduleCriteria";

const definition = {
  category: { id: 1 },
  type: { id: 2 },
  mode: { id: 3 },
  attributes: [5, 4],
} as SurveyFormState;

describe("survey module criteria", () => {
  it("compares selected IDs and treats attribute order as irrelevant", () => {
    expect(
      haveModuleCriteriaChanged(definition, {
        category: { id: 1 },
        type: { id: 2 },
        mode: { id: 3 },
        attributes: [4, 5],
      } as SurveyFormState),
    ).toBe(false);
  });

  it.each([
    ["category", { category: { id: 9 } }],
    ["type", { type: { id: 9 } }],
    ["mode", { mode: { id: 9 } }],
    ["attributes", { attributes: [4] }],
  ])("detects a changed %s", (_field, change) => {
    expect(
      haveModuleCriteriaChanged(definition, {
        ...definition,
        ...change,
      }),
    ).toBe(true);
  });

  it("clears module-dependent choices while preserving survey definition", () => {
    const surveyData = {
      ...definition,
      name: "Survey",
      organizations: [],
      modules_order: [10],
      submodules: [20],
      submodules_order: [20],
      indicators: [30],
      indicator_areas_order: [40],
      indicators_order: { 40: [30] },
      sub_questions: [{ id: 50 }],
      languages: [{ language: "en", language_display: "English" }],
    } as unknown as SurveyFormState;

    expect(clearModuleDependentSurveyData(surveyData)).toEqual({
      ...surveyData,
      modules_order: [],
      submodules: [],
      submodules_order: [],
      indicators: [],
      indicator_areas_order: [],
      indicators_order: {},
      sub_questions: [],
    });
  });
});
