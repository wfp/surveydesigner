import { Module } from "../../types/api";
import { API } from "../../utils";
import { modulesActions } from "../reducers/modulesReducer";
import { createAppAsyncThunk } from "../store";

export const fetchModules = createAppAsyncThunk(
  "modules/FETCH_MODULES",
  (_, { dispatch, getState }) => {
    const { surveyForm } = getState();

    const params = {
      category: surveyForm.category ? surveyForm.category.id : null,
      type: surveyForm.type ? surveyForm.type.id : null,
      mode: surveyForm.mode ? surveyForm.mode.id : null,
      attributes: surveyForm.attributes.join(","),
    };

    dispatch(modulesActions.getModules());
    API.get<Module[]>("/modules/", { params })
      .then((res) => {
        dispatch(modulesActions.setModules(res.data));
      })
      .catch((err) => {
        dispatch(modulesActions.setModulesError(err));
      });
  }
);
