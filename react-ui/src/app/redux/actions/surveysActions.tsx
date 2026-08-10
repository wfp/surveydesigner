import { Surveys } from "../../types/api";
import { API } from "../../utils";
import { surveysActions } from "../reducers/surveysReducer";
import { createAppAsyncThunk } from "../store";

function organizationScopeKey(organizations: { id: number }[]) {
  return organizations.map(({ id }) => id).join(",");
}

export const fetchSurveys = createAppAsyncThunk(
  "surveys/FETCH_SURVEYS",
  (preserveCurrentData = false, { dispatch, getState }) => {
    const requestedOrganizationScope = organizationScopeKey(
      getState().surveyForm.organizations,
    );
    dispatch(surveysActions.getSurveys(preserveCurrentData));
    API.get<Surveys>("/surveys/")
      .then((res) => {
        // A copied survey can trigger an initial request before its
        // organizations are committed to Redux. Ignore that response if the
        // selected organization scope has since changed.
        if (
          organizationScopeKey(getState().surveyForm.organizations) !==
          requestedOrganizationScope
        ) {
          return;
        }
        dispatch(surveysActions.setSurveys(res.data));
      })
      .catch((err) => {
        if (
          organizationScopeKey(getState().surveyForm.organizations) !==
          requestedOrganizationScope
        ) {
          return;
        }
        dispatch(surveysActions.setSurveysError(err));
      });
  },
);
