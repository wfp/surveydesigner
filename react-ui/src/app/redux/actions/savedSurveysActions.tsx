import { AxiosResponse } from "axios";
import { Cookies } from "react-cookie";
import { ApiError } from "../../types";
import { SavedSurvey } from "../../types/api";
import { API } from "../../utils";
import { savedSurveysActions } from "../reducers/savedSurveysReducer";
import { createAppAsyncThunk } from "../store";
import { SurveyFormState } from "../reducers/surveyFormReducer";
import { notificationsActions } from "../reducers/notificationReducer";

export const fetchSavedSurveys = createAppAsyncThunk(
  "saved_surveys/FETCH_SAVEDSURVEYS",
  async (
    filters: {
      [key: string]: unknown;
    },
    { dispatch, getState },
  ) => {
    dispatch(savedSurveysActions.getSavedSurveys());

    const params: {
      [key: string]: unknown;
    } = {};

    // Loop over filters object and add to params
    Object.keys(filters).forEach((key) => {
      params[key] = filters[key];
    });

    try {
      const res = await API.get<SavedSurvey[]>("/saved-surveys/", { params });
      dispatch(savedSurveysActions.setSavedSurveys(res.data));
      dispatch(savedSurveysActions.completeInitialRequest());
      return res;
    } catch (err: any) {
      dispatch(savedSurveysActions.setSavedSurveysError(err));
    }
  },
);

// Function to link a question to a submodule in the backend.
const formatSubQuestions = (subquestions: any[]) => {
  const submodules: { [key: string]: any[] } = {};
  subquestions.forEach((subquestion) => {
    if (typeof subquestion.id === "string") return;

    if (submodules[subquestion.submodule]) {
      submodules[subquestion.submodule].push(subquestion.id);
    } else {
      submodules[subquestion.submodule] = [subquestion.id];
    }
  });
  return submodules;
};

// Utility function to extract error message
const extractErrorMessage = (err: ApiError) => {
  // Check if err.response and err.response.data exist
  if (err.response && err.response.data && err.response.data.message) {
    return err.response.data.message;
  }
  // Fallback message if above conditions are not met
  return err.message || "An unknown error occurred";
};

const getDataForSave = (timestamp: string, surveyForm: SurveyFormState) => ({
  name: surveyForm.name || `survey_${timestamp}`,
  // Ensure organizations is always an array before mapping
  organizations: (surveyForm.organizations || []).map((org) => org.id),
  survey_type: surveyForm.type ? surveyForm.type.id : null,
  survey_category: surveyForm.category ? surveyForm.category.id : null,
  survey_mode: surveyForm.mode ? surveyForm.mode.id : null,
  indicators: surveyForm.indicators,
  modules_order: surveyForm.modules_order,
  submodules: surveyForm.submodules,
  attributes: surveyForm.attributes,
  languages: surveyForm.languages,
  indicator_areas_order: surveyForm.indicator_areas_order,
  indicators_order: surveyForm.indicators_order,
  subquestions: formatSubQuestions(surveyForm.sub_questions),
  submodules_order: surveyForm.submodules_order,
});

export const postSavedSurvey = createAppAsyncThunk(
  "saved_surveys/POST_SAVEDSURVEYS",
  async (survey: SurveyFormState, { dispatch, getState }) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    const timestamp = new Date().getTime().toString();
    const data = getDataForSave(timestamp, survey);

    try {
      const response = await API.post("/saved-surveys/", data, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      dispatch(
        notificationsActions.setSuccessNotification({
          msg: "Survey saved successfully",
        }),
      );
      return response.data;
    } catch (err: any) {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: extractErrorMessage(err),
          title: "Error Saving Survey",
        }),
      );
      dispatch(savedSurveysActions.setSavedSurveysError(err));
      throw err;
    }
  },
);

interface PutSurveyParams extends SurveyFormState {
  uuid: number | string;
}

export const putSavedSurvey = createAppAsyncThunk(
  "saved_surveys/PUT_SAVEDSURVEYS",
  async ({ uuid, ...survey }: PutSurveyParams, { dispatch, getState }) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    const timestamp = new Date().getTime().toString();
    const data = getDataForSave(timestamp, survey);
    try {
      const response = await API.put(`/saved-surveys/${uuid}/`, data, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      dispatch(
        notificationsActions.setSuccessNotification({
          msg: "Survey Updated successfully",
        }),
      );
      return response.data;
    } catch (err: any) {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: extractErrorMessage(err),
          title: "Error Saving Survey",
        }),
      );
      dispatch(savedSurveysActions.setSavedSurveysError(err));
      throw err;
    }
  },
);

interface DeleteSavedSurveyParams {
  uuid: number | null;
}

export const deleteSavedSurvey = createAppAsyncThunk(
  "saved_surveys/DELETE_SAVEDSURVEYS",
  async ({ uuid }: DeleteSavedSurveyParams, { dispatch, getState }) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");

    try {
      if (!uuid || uuid === null) throw new Error("No survey id provided");
      const response = await API.delete(`/saved-surveys/${uuid}/`, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      dispatch(
        notificationsActions.setSuccessNotification({
          msg: "Survey Delete successfully",
        }),
      );
      return response;
    } catch (err: any) {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: extractErrorMessage(err),
          title: "Error Deleting Survey",
        }),
      );
      dispatch(savedSurveysActions.setSavedSurveysError(err));
      throw err;
    }
  },
);

interface getSavedSurveyParams {
  uuid: number | string | null;
}

export const fetchSavedSurvey = createAppAsyncThunk(
  "saved_surveys/GET_SAVEDSURVEY",
  async ({ uuid }: getSavedSurveyParams, { dispatch, getState }) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    dispatch(savedSurveysActions.getSavedSurveys());

    try {
      if (!uuid || uuid === null) throw new Error("No survey id provided");
      const response = await API.get(`/saved-surveys/${uuid}/`, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      dispatch(savedSurveysActions.setSavedSurveyDetail(response.data));
      return response;
    } catch (err: any) {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: extractErrorMessage(err),
          title: `Error Getting Survey: ID: ${uuid}`,
        }),
      );
      dispatch(savedSurveysActions.setSavedSurveysError(err));
      throw err;
    }
  },
);

interface getSavedSurveyParams {
  uuid: number | string | null;
}

export const getSavedSurveyCopy = createAppAsyncThunk(
  "saved_surveys/POST_SAVEDSURVEY_copy",
  async ({ uuid }: getSavedSurveyParams, { dispatch, getState }) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    dispatch(savedSurveysActions.getSavedSurveys());
    let response: AxiosResponse<SavedSurvey> | undefined;

    try {
      if (!uuid || uuid === null) throw new Error("No survey id provided");
      response = await API.get(`/saved-surveys/${uuid}/copy/`, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      dispatch(savedSurveysActions.setSavedSurveyDetail(response.data));
      dispatch(
        notificationsActions.setSuccessNotification({
          msg: "Survey Copied successfully",
        }),
      );
    } catch (err: any) {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: extractErrorMessage(err),
          title: `Error Copying Survey: ID: ${uuid}`,
        }),
      );
      dispatch(savedSurveysActions.setSavedSurveysError(err));
      throw err;
    }
    return response;
  },
);
