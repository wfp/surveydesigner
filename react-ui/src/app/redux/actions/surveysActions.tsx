import { Surveys } from "../../types/api";
import { API } from "../../utils";
import { surveysActions } from "../reducers/surveysReducer";
import { createAppAsyncThunk } from "../store";

export const fetchSurveys = createAppAsyncThunk(
  "surveys/FETCH_SURVEYS",
  (_, { dispatch, getState }) => {
    dispatch(surveysActions.getSurveys());
    API.get<Surveys>("/surveys/")
      .then((res) => {
        dispatch(surveysActions.setSurveys(res.data));
      })
      .catch((err) => {
        dispatch(surveysActions.setSurveysError(err));
      });
  }
);
