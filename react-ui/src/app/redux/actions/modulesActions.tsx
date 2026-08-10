import { Module } from "../../types/api";
import { API } from "../../utils";
import { modulesActions } from "../reducers/modulesReducer";
import { createAppAsyncThunk } from "../store";

function moduleCriteriaKey(surveyForm: {
  category?: { id: number } | null;
  type?: { id: number } | null;
  mode?: { id: number } | null;
  attributes: number[];
  organizations: { id: number }[];
}) {
  return [
    surveyForm.category?.id ?? "",
    surveyForm.type?.id ?? "",
    surveyForm.mode?.id ?? "",
    surveyForm.attributes.join(","),
    surveyForm.organizations.map(({ id }) => id).join(","),
  ].join("|");
}

export const fetchModules = createAppAsyncThunk(
  "modules/FETCH_MODULES",
  (_, { dispatch, getState }) => {
    const { surveyForm } = getState();
    const requestedCriteriaKey = moduleCriteriaKey(surveyForm);

    const params = {
      category: surveyForm.category ? surveyForm.category.id : null,
      type: surveyForm.type ? surveyForm.type.id : null,
      mode: surveyForm.mode ? surveyForm.mode.id : null,
      attributes: surveyForm.attributes.join(","),
    };

    dispatch(modulesActions.getModules());
    API.get<Module[]>("/modules/", { params })
      .then((res) => {
        // A criteria change can start a second request before the first one
        // returns. Do not let the older response replace the current module
        // list with an empty or unrelated result.
        if (moduleCriteriaKey(getState().surveyForm) !== requestedCriteriaKey) {
          return;
        }
        dispatch(modulesActions.setModules(res.data));
      })
      .catch((err) => {
        if (moduleCriteriaKey(getState().surveyForm) !== requestedCriteriaKey) {
          return;
        }
        dispatch(modulesActions.setModulesError(err));
      });
  },
);
