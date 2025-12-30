import { API } from "../../utils";
import { createAppAsyncThunk } from "../store";
import { indicatorsActions } from "../reducers/indicatorsReducer";
import { Indicator } from "../../types/api";

export const fetchIndicators = createAppAsyncThunk(
  "indicators/FETCH_INDICATORS",
  (_, { dispatch, getState }) => {
    const { surveyForm } = getState();

    const params = {
      type: surveyForm.type ? surveyForm.type.id : null,
      mode: surveyForm.mode ? surveyForm.mode.id : null,
    };

    dispatch(indicatorsActions.getIndicators());
    API.get<Indicator[]>("/indicators/", { params })
      .then((res) => {
        dispatch(indicatorsActions.setIndicators(res.data));
      })
      .catch((err) => {
        dispatch(indicatorsActions.setIndicatorsError(err));
      });
  }
);
