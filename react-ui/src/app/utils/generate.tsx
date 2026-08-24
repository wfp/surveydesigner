/* eslint-disable camelcase */
import { Cookies } from "react-cookie";
import { ModulesData } from "../contexts/ModulesContext.interface";
import { API } from ".";
import { downloadFile } from "./download";
import { notificationsActions } from "../redux/reducers/notificationReducer";
import { docFetcherActions } from "../redux/reducers/docFetcherReducer";
import { AppDispatch } from "../redux/store";
import {
  formatValidationIssues,
  getApiErrorTitle,
  parseApiError,
  parseValidationWarningsHeader,
  renderApiErrorMessage,
} from "./apiError";

export function getOrderedSubmodules(
  surveyForm: any,
  modulesData: React.MutableRefObject<ModulesData>,
) {
  const allOrderedSubmodules: number[] = [];
  if (modulesData) {
    modulesData.current.modules_order.forEach((moduleID) => {
      allOrderedSubmodules.push(
        ...modulesData.current.submodules_order[moduleID],
      );
    });
    return allOrderedSubmodules.filter((submoduleID) =>
      surveyForm.submodules.includes(submoduleID),
    );
  }

  surveyForm.submodules.forEach((moduleID: number) => {
    allOrderedSubmodules.push(moduleID);
  });
  return allOrderedSubmodules;
}

export function getDataForGeneration(
  surveyForm: any,
  modulesData: React.MutableRefObject<ModulesData>,
  isSharedSurvey = false,
) {
  const timestamp = new Date().getTime().toString();

  let submodules_order;
  let sub_questions;
  let survey_type;
  let languages;

  if (modulesData && !isSharedSurvey) {
    submodules_order = modulesData.current.modules_order.flatMap(
      (moduleId) => modulesData.current.submodules_order[moduleId],
    );
    sub_questions = surveyForm.sub_questions.map((item: any) => item.id);
    sub_questions = sub_questions.filter((sub_question: any) => {
      return String(sub_question).split("-").length <= 1;
    });
    survey_type = surveyForm.type ? surveyForm.type.id : null;
    languages =
      surveyForm.languages &&
      surveyForm.languages.map((item: any) => item.language);
  } else {
    submodules_order = surveyForm.submodules_order;
    sub_questions = Object.keys(
      surveyForm.subquestion_submodule_mapping,
    ).flatMap((key: any) =>
      surveyForm.subquestion_submodule_mapping[key].map((item: any) => item.id),
    );
    survey_type = surveyForm.survey_type ? surveyForm.survey_type.id : null;
    // Handle languages directly for shared surveys or fallback
    languages = isSharedSurvey
      ? (surveyForm.languages || []).map((item: any) => item.language)
      : ["en"];
  }
  return {
    name: surveyForm.name || `survey_${timestamp}`,
    survey_type,
    submodules: getOrderedSubmodules(surveyForm, modulesData),
    sub_questions,
    submodules_order,
    languages,
    indicators: surveyForm.indicators,
  };
}

export const getXLS = (
  dispatch: AppDispatch,
  surveyForm: any,
  modulesData?: any,
  isSharedSurvey = false,
) => {
  const timestamp = new Date().getTime().toString();
  const data = getDataForGeneration(surveyForm, modulesData, isSharedSurvey);
  const cookies = new Cookies();
  const csrfToken = cookies.get("csrftoken");
  return API.post("/generate/", data, {
    responseType: "blob",
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((res) => {
      const contentType = res.headers["content-type"];
      let mimeType =
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      let extension = "xlsx";

      if (contentType?.startsWith("application/zip")) {
        mimeType = "application/zip";
        extension = "zip";
      }

      downloadFile(res, timestamp, mimeType, extension);
      const warnings = parseValidationWarningsHeader(
        res.headers["x-survey-validation-warnings"] ||
          res.headers["x-validation-warnings"],
      );
      if (warnings.length) {
        dispatch(
          notificationsActions.setWarnNotification({
            title: "Download completed with warnings",
            msg: formatValidationIssues(warnings).join("\n"),
          }),
        );
      }
    })
    .catch(async (err) => {
      const parsedError = await parseApiError(err);
      dispatch(
        notificationsActions.setErrorNotification({
          msg: renderApiErrorMessage(parsedError, "Error getting XLS file."),
          title: getApiErrorTitle(parsedError, "Error getting XLS file."),
        }),
      );
    });
};

export const generateDoc = (
  dispatch: AppDispatch,
  surveyForm: any,
  modulesData?: any,
  isSharedSurvey = false,
) => {
  const data = getDataForGeneration(surveyForm, modulesData, isSharedSurvey);
  const cookies = new Cookies();
  const csrfToken = cookies.get("csrftoken");
  API.post("/generate-doc/", data, {
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((res) => {
      const {
        status: statusRes,
        position: positionRes,
        jobId: jobIdRes,
      } = res.data;
      dispatch(
        docFetcherActions.setJobId({
          jobId: jobIdRes,
          status: statusRes,
          position: positionRes,
        }),
      );
    })
    .catch((err) => {
      dispatch(
        notificationsActions.setErrorNotification({
          msg: renderApiErrorMessage(err, "Error getting Word file."),
          title: "Error getting Word file.",
        }),
      );
    });
};
