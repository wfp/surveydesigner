import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";

type ModuleCriteria = Pick<
  SurveyFormState,
  "category" | "type" | "mode" | "attributes"
>;

function getId(value: { id: number } | null | undefined) {
  return value?.id ?? null;
}

function getSortedAttributeIds(attributes: number[] | null | undefined) {
  return [...(attributes || [])].sort((left, right) => left - right);
}

export function haveModuleCriteriaChanged(
  previous: ModuleCriteria,
  next: ModuleCriteria,
) {
  return (
    getId(previous.category) !== getId(next.category) ||
    getId(previous.type) !== getId(next.type) ||
    getId(previous.mode) !== getId(next.mode) ||
    JSON.stringify(getSortedAttributeIds(previous.attributes)) !==
      JSON.stringify(getSortedAttributeIds(next.attributes))
  );
}

export function clearModuleDependentSurveyData(
  surveyData: SurveyFormState,
): SurveyFormState {
  return {
    ...surveyData,
    modules_order: [],
    submodules: [],
    submodules_order: [],
    indicators: [],
    indicator_areas_order: [],
    indicators_order: {},
    sub_questions: [],
  };
}
