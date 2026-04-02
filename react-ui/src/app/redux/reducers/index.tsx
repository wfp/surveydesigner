import { combineReducers } from "@reduxjs/toolkit";

import appReducer from "./appReducer";
import authReducer from "./authReducer";
import indicatorsReducer from "./indicatorsReducer";
import indicatorAreasReducer from "./indicatorAreasReducer";
import moduleReducer from "./modulesReducer";
import submodulesReducer from "./submodulesReducer";
import surveysReducer from "./surveysReducer";
import surveyFormReducer from "./surveyFormReducer";
import projectsReducer from "./projectsReducer";
import docFetcherReducer from "./docFetcherReducer";
import notificationReducer from "./notificationReducer";
import organizationsReducer from "./organizationsReducer";
import frontendContentReducer from "./frontendContentReducer";
import savedSurveysReducer from "./savedSurveysReducer";
import surveyWizardUiReducer from "./surveyWizardUiReducer";

const rootReducer = combineReducers({
  app: appReducer,
  notification: notificationReducer,
  auth: authReducer,
  modules: moduleReducer,
  submodules: submodulesReducer,
  indicators: indicatorsReducer,
  indicatorAreas: indicatorAreasReducer,
  surveys: surveysReducer,
  projects: projectsReducer,
  surveyForm: surveyFormReducer,
  docFetcher: docFetcherReducer,
  organizations: organizationsReducer,
  frontendContent: frontendContentReducer,
  savedSurveys: savedSurveysReducer,
  surveyWizardUi: surveyWizardUiReducer,
});

// Exports

export default rootReducer;
