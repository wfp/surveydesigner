import { API } from "../../utils";
import { createAppAsyncThunk } from "../store";
import { submodulesActions } from "../reducers/submodulesReducer";
import { SubmoduleWithQuestions } from "../../types/api";

export const fetchSubmodules = createAppAsyncThunk(
  "submodules/FETCH_SUBMODULES",
  (_, { dispatch, getState }) => {
    const { surveyForm } = getState();

    const params = {
      submodule_ids: surveyForm.submodules.join(","),
      indicator_ids: surveyForm.indicators
        ? surveyForm.indicators.join(",")
        : null,
    };

    dispatch(submodulesActions.getSubmodules());
    API.get<SubmoduleWithQuestions[]>("/submodules/", { params })
      .then((res) => {
        dispatch(submodulesActions.setSubmodules(res.data));
      })
      .catch((err) => {
        dispatch(submodulesActions.setSubmodulesError(err));
      });
  }
);
