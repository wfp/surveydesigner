import React, { useCallback, useEffect, useRef, useState } from "react";

import {
  Module,
  ModuleBody,
  ModuleHeader,
  Wrapper,
} from "@wfp/react";

import { useNavigate, useLocation } from "react-router-dom";
import { SurveyWizardFooter } from "./UI/SurveyWizardFooter";

import { PayloadAction } from "@reduxjs/toolkit";
import { useTranslation } from "react-i18next";
import MainLayout from "../Layout";
import Modules from "../Modules";
import Surveys from "../Surveys";
import Review from "../Review";
import Generate from "../Generate";
import DocFetcher from "../DocFetcher";
import { ModulesProvider } from "../../contexts/ModulesContext";
import { fetchFrontendContent } from "../../redux/actions/frontendContentActions";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { PrevNextStepCallback } from "../../types";
import {
  fetchSavedSurveys,
  postSavedSurvey,
  putSavedSurvey,
} from "../../redux/actions/savedSurveysActions";
import { savedSurveysActions } from "../../redux/reducers/savedSurveysReducer";

import SurveyTable from "../SurveyTable";
import {
  SurveyCategory,
  SurveyMode,
  SurveyTypes,
} from "../../types/api";
import { surveyFormActions } from "../../redux/reducers/surveyFormReducer";
import {
  DeleteSavedSurveyModal,
  DeleteSavedSurveyModalOptionsInterface,
} from "../DeleteSavedSurveyModal";
import {
  ShareSurveyModal,
  ShareSavedSurveyModalOptionsInterface,
} from "../ShareSurveyModal";
import { modulesActions } from "../../redux/reducers/modulesReducer";
import { StepNavigationWrapper } from "./UI/StepNavigationWrapper";
import { SurveyWizardHeader } from "./UI/SurveyWizardHeader";
import { surveyWizardUiActions } from "../../redux/reducers/surveyWizardUiReducer";

function SurveyWizard() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const [deleteSavedSurveyModalOptions, setDeleteSavedSurveyModalOptions] =
    useState<DeleteSavedSurveyModalOptionsInterface>({
      uuid: null,
      isOpen: false,
    });
  const [shareSavedSurveyModalOptions, setShareSavedSurveyModalOptions] =
    useState<ShareSavedSurveyModalOptionsInterface>({
      uuid: null,
      isOpen: false,
    });
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const { step, goToStep, isCreatingSurvey, selectedSurveyToEdit } =
    useAppSelector((state) => state.surveyWizardUi);

  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const initialRequest = useAppSelector(
    (state) => state.savedSurveys.initialRequest,
  );

  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as {
    surveyId?: number | string;
    copiedSurvey?: any;
  };

  const paths = ["survey", "modules", "review", "generate"];

  useEffect(() => {
    // If a copiedSurvey is present in navigation state, use it directly
    if (state && state.copiedSurvey) {
      dispatch(surveyWizardUiActions.setSelectedSurveyToEdit(state.copiedSurvey));
      dispatch(surveyWizardUiActions.setIsCreatingSurvey(true));
      return;
    }
    if (!savedSurveys.data) {
      dispatch(fetchSavedSurveys({})).then((res: any) => {
        if (state && state.surveyId) {
          const data = res?.payload;
          if (Array.isArray(data)) {
            const selectedSurveyFromCopy = data.find(
              (survey) => survey.uuid === state.surveyId,
            );
            if (selectedSurveyFromCopy) {
              dispatch(
                surveyWizardUiActions.setSelectedSurveyToEdit(
                  selectedSurveyFromCopy,
                ),
              );
              dispatch(surveyWizardUiActions.setIsCreatingSurvey(true));
            }
          }
        } else {
          const data = res?.payload;
          if (Array.isArray(data) && data.length > 0) {
            dispatch(surveyWizardUiActions.setIsCreatingSurvey(false));
          }
        }
      });
      dispatch(savedSurveysActions.completeInitialRequest());
    }
  }, []);

  const next: PrevNextStepCallback = useCallback(
    (nextCallback, prevCallback) => {
      if (step !== goToStep) {
        const proceed = () => {
          dispatch(surveyWizardUiActions.setStep(goToStep));
          navigate(`/design/${paths[goToStep]}`);
        };

        if (goToStep > step) {
          if (nextCallback) {
            nextCallback(proceed, step);
          } else {
            proceed();
          }
        } else if (prevCallback) {
          prevCallback();
        } else {
          proceed();
          dispatch(surveyWizardUiActions.setIsValidating(false));
        }

        dispatch(surveyWizardUiActions.setPrvsStep(step));
      }
    },
    [dispatch, goToStep, navigate, step],
  );

  useEffect(() => {
    const startingPath = `/design/${paths[0]}`;
    if (window.location.pathname !== startingPath) {
      navigate(startingPath);
    }
    if (!frontendContent) {
      dispatch(fetchFrontendContent());
    }
  }, []);

  const sidebar = <StepNavigationWrapper />;

  function resetSurveyData() {
    dispatch(surveyWizardUiActions.resetToSurveyList());
    dispatch(surveyFormActions.resetSurveyData({}));
    dispatch(fetchSavedSurveys({}));
  }

  function isSavedSurveyActionSuccess(
    res: PayloadAction<any>,
    actionType: string,
  ) {
    if (res.type === actionType) {
      resetSurveyData();
    }
  }

  const saveSurvey = async () => {
    if (selectedSurveyToEdit && selectedSurveyToEdit.uuid) {
      dispatch(
        putSavedSurvey({ ...surveyForm, uuid: selectedSurveyToEdit.uuid }),
      ).then((res) => {
        isSavedSurveyActionSuccess(
          res,
          "saved_surveys/PUT_SAVEDSURVEYS/fulfilled",
        );
      });
    } else {
      dispatch(postSavedSurvey(surveyForm)).then((res) => {
        isSavedSurveyActionSuccess(
          res,
          "saved_surveys/POST_SAVEDSURVEYS/fulfilled",
        );
      });
    }
  };

  type ValueTypes = {
    category: SurveyCategory | null | undefined;
    type: SurveyTypes | null | undefined;
    mode: SurveyMode | null | undefined;
    attributes: number[] | null;
  };

  const prevValues = useRef<ValueTypes>({
    category: null,
    type: null,
    mode: null,
    attributes: null,
  });

  const currentValues = {
    category: surveyForm.category,
    type: surveyForm.type,
    mode: surveyForm.mode,
    attributes: surveyForm.attributes,
  };

  const surveyTableRef = useRef<{ clearFilters: () => void }>(null);
  useEffect(() => {
    if (step === 1 && !selectedSurveyToEdit) {
      // Check if any of the four fields have changed
      if (
        JSON.stringify(prevValues.current) !== JSON.stringify(currentValues)
      ) {
        dispatch(modulesActions.clearModules());
        prevValues.current = currentValues;
      }
    }
  }, [step, selectedSurveyToEdit, currentValues, dispatch]);

  const savedSurveyLabelsData = savedSurveys.data
    ? savedSurveys.data.map((survey) =>
        Object.entries(survey).reduce<{ [key: string]: unknown }>(
          (newSurvey, [key, value]) => {
            // For each property, if the value is an object, replace it with its name or label
            if (value && typeof value === "object") {
              // if the value is an array, map through it and join the names or labels into a string
              if (Array.isArray(value)) {
                newSurvey[key] = value
                  .map((item) => item.name || item.label)
                  .join(", ");
              } else {
                newSurvey[key] = value.name || value.label;
              }
            } else {
              newSurvey[key] = value;
            }
            return newSurvey;
          },
          {},
        ),
      )
    : [];
  const tableContent = (
    <div>
      <SurveyTable
        ref={surveyTableRef}
        data={savedSurveyLabelsData}
        isFetching={savedSurveys.isLoading}
        count={savedSurveyLabelsData ? savedSurveyLabelsData.length : 0}
        actions={{
          edit: (surveyID: number) => {
            dispatch(modulesActions.clearModules());
            const survey =
              savedSurveys.data !== null
                ? savedSurveys.data.find(
                    (savedSurvey) => savedSurvey.uuid === surveyID,
                  )
                : null;
            dispatch(surveyWizardUiActions.setIsCreatingSurvey(true));
            dispatch(surveyWizardUiActions.setSelectedSurveyToEdit(survey || null));
          },
          delete: (surveyID: number) => {
            setDeleteSavedSurveyModalOptions({ uuid: surveyID, isOpen: true });
          },
          share: (surveyID: number) => {
            setShareSavedSurveyModalOptions({ uuid: surveyID, isOpen: true });
          },
        }}
      />
    </div>
  );
  const step0Content =
    initialRequest || isCreatingSurvey ? (
      <Surveys
        next={next}
        frontendContent={frontendContent}
        selectedSurveyToEdit={selectedSurveyToEdit}
      />
    ) : (
      tableContent
    );
  return (
    <MainLayout
      title={t("surveyWizard.title")}
      subTitle={t("surveyWizard.subTitle")}
    >
      <DocFetcher />
      <DeleteSavedSurveyModal
        deleteSavedSurveyModalOptions={deleteSavedSurveyModalOptions}
        isSavedSurveyActionSuccess={isSavedSurveyActionSuccess}
        setDeleteSavedSurveyModalOptions={setDeleteSavedSurveyModalOptions}
        selectedSavedSurvey={savedSurveys.data?.find(
          (survey) => survey.uuid === deleteSavedSurveyModalOptions.uuid,
        )}
      />
      <ShareSurveyModal
        shareSavedSurveyModalOptions={shareSavedSurveyModalOptions}
        setShareSavedSurveyModalOptions={setShareSavedSurveyModalOptions}
        selectedSavedSurvey={savedSurveys.data?.find(
          (survey) => survey.uuid === shareSavedSurveyModalOptions.uuid,
        )}
      />
      <Wrapper pageWidth="lg">
        <div className="wfp--form-wizard survey-wizard">
          <aside className="wfp--form-wizard__sidebar">{sidebar}</aside>
          <Module className="survey-module">
            <ModuleHeader>
              <SurveyWizardHeader />
            </ModuleHeader>
            <ModulesProvider>
              <ModuleBody className="survey-content">
                {step === 0 && step0Content}
                {step === 1 && <Modules next={next} />}
                {step === 2 && <Review next={next} />}
                {step === 3 && <Generate next={next} />}
              </ModuleBody>
            </ModulesProvider>
            <SurveyWizardFooter
              onPreviousClick={() => {
                if (step > 0) {
                  dispatch(surveyWizardUiActions.goPrevious());
                } else {
                  dispatch(surveyWizardUiActions.setIsCreatingSurvey(false));
                  resetSurveyData();
                }
              }}
              onCreateSurveyClick={() => {
                dispatch(surveyWizardUiActions.setIsCreatingSurvey(true));
                if (surveyTableRef.current) {
                  surveyTableRef.current.clearFilters();
                }
              }}
              onSaveClick={() => {
                void saveSurvey();
              }}
            />
          </Module>
        </div>
      </Wrapper>
    </MainLayout>
  );
}

export default SurveyWizard;
