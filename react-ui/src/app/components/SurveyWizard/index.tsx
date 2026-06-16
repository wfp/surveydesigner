import React, { useCallback, useEffect, useRef } from "react";

import { Module, ModuleBody, Wrapper } from "@wfp/react";

import { useNavigate, useLocation } from "react-router-dom";

import { PayloadAction } from "@reduxjs/toolkit";
import { useTranslation } from "react-i18next";
import MainLayout from "../Layout";
import Modules from "../Modules";
import Surveys from "../Surveys";
import Review from "../Review";
import Generate from "../Generate";
import DocFetcher from "../DocFetcher";
import { ModulesProvider } from "../../contexts/ModulesContext";
import {
  SurveyWizardProvider,
  useSurveyWizardContext,
} from "../../contexts/SurveyWizardContext";
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
  SavedSurvey,
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
import SurveyWizardFooter from "./Footer";
import SurveyWizardHeader from "./Header";
import SurveyWizardStepNavigation from "./StepNavigation";

type LocationState = {
  surveyId?: number | string;
  copiedSurvey?: SavedSurvey;
};

type SavedSurveyTableRef = {
  clearFilters: () => void;
};

type SurveyValues = {
  category: SurveyCategory | null | undefined;
  type: SurveyTypes | null | undefined;
  mode: SurveyMode | null | undefined;
  attributes: number[] | null;
};

function SurveyWizardContent() {
  const dispatch = useAppDispatch();
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const initialRequest = useAppSelector(
    (state) => state.savedSurveys.initialRequest,
  );
  const {
    step,
    setStep,
    setPrvsStep,
    goToStep,
    setGoToStep,
    paths,
    modulesContextKey,
    refreshModulesContext,
    isCreatingSurvey,
    setIsCreatingSurvey,
    selectedSurveyToEdit,
    setSelectedSurveyToEdit,
    setIsValidating,
  } = useSurveyWizardContext();
  const [deleteSavedSurveyModalOptions, setDeleteSavedSurveyModalOptions] =
    React.useState<DeleteSavedSurveyModalOptionsInterface>({
      uuid: null,
      isOpen: false,
    });
  const [shareSavedSurveyModalOptions, setShareSavedSurveyModalOptions] =
    React.useState<ShareSavedSurveyModalOptionsInterface>({
      uuid: null,
      isOpen: false,
    });
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as LocationState;
  const surveyTableRef = useRef<SavedSurveyTableRef>(null);
  const prevValues = useRef<SurveyValues>({
    category: null,
    type: null,
    mode: null,
    attributes: null,
  });

  const next = useCallback(
    (): PrevNextStepCallback => (nextCallback, prevCallback) => {
      if (step !== goToStep) {
        const proceed = () => {
          setStep(goToStep);
          navigate(`/design/${paths[goToStep]}`);
        };

        if (goToStep > step) {
          if (nextCallback) {
            nextCallback(proceed, step, setGoToStep);
          } else {
            proceed();
          }
        } else if (prevCallback) {
          prevCallback();
        } else {
          proceed();
          setIsValidating(false);
        }

        setPrvsStep(step);
      }
    },
    [
      goToStep,
      navigate,
      paths,
      setGoToStep,
      setIsValidating,
      setPrvsStep,
      setStep,
      step,
    ],
  );

  useEffect(() => {
    if (state && state.copiedSurvey) {
      setSelectedSurveyToEdit(state.copiedSurvey);
      refreshModulesContext();
      setIsCreatingSurvey(true);
      return;
    }
    if (!savedSurveys.data) {
      dispatch(fetchSavedSurveys({})).then((res: any) => {
        if (state && state.surveyId) {
          const data = res?.payload?.data;
          if (Array.isArray(data)) {
            const selectedSurveyFromCopy = data.find(
              (survey: SavedSurvey) => survey.uuid === state.surveyId,
            );
            if (selectedSurveyFromCopy) {
              setSelectedSurveyToEdit(selectedSurveyFromCopy);
              refreshModulesContext();
              setIsCreatingSurvey(true);
            }
          }
        }
      });
      dispatch(savedSurveysActions.completeInitialRequest());
    }
  }, []);

  useEffect(() => {
    const startingPath = `/design/${paths[0]}`;
    if (window.location.pathname !== startingPath) {
      navigate(startingPath);
    }
    if (!frontendContent) {
      dispatch(fetchFrontendContent());
    }
  }, []);

  const currentValues = {
    category: surveyForm.category,
    type: surveyForm.type,
    mode: surveyForm.mode,
    attributes: surveyForm.attributes,
  };

  useEffect(() => {
    if (step === 1 && !selectedSurveyToEdit) {
      if (
        JSON.stringify(prevValues.current) !== JSON.stringify(currentValues)
      ) {
        dispatch(modulesActions.clearModules());
        prevValues.current = currentValues;
      }
    }
  }, [step, selectedSurveyToEdit, currentValues, dispatch]);

  function resetSurveyData() {
    dispatch(fetchSavedSurveys({}));
    setGoToStep(0);
    setIsCreatingSurvey(false);
    setSelectedSurveyToEdit(null);
    refreshModulesContext();
    dispatch(surveyFormActions.resetSurveyData({}));
  }

  function startCreatingSurvey() {
    setIsCreatingSurvey(true);
    setSelectedSurveyToEdit(null);
    dispatch(surveyFormActions.resetSurveyData({}));
    refreshModulesContext();
    surveyTableRef.current?.clearFilters();
  }

  function isSavedSurveyActionSuccess(
    res: PayloadAction<any>,
    actionType: string,
  ) {
    if (res.type === actionType) {
      resetSurveyData();
    }
  }

  const saveSurvey = () => {
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

  const savedSurveyLabelsData = savedSurveys.data
    ? savedSurveys.data.map((survey) =>
        Object.entries(survey).reduce<{ [key: string]: unknown }>(
          (newSurvey, [key, value]) => {
            if (value && typeof value === "object") {
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
    <SurveyTable
      ref={surveyTableRef}
      data={savedSurveyLabelsData}
      isFetching={savedSurveys.isLoading}
      count={savedSurveyLabelsData ? savedSurveyLabelsData.length : 0}
      onCreateSurvey={startCreatingSurvey}
      actions={{
        edit: (surveyID: number) => {
          dispatch(modulesActions.clearModules());
          const survey =
            savedSurveys.data !== null
              ? savedSurveys.data.find(
                  (savedSurvey: SavedSurvey) => savedSurvey.uuid === surveyID,
                )
              : null;
          setIsCreatingSurvey(true);
          refreshModulesContext();
          setSelectedSurveyToEdit(survey || null);
        },
        delete: (surveyID: number) => {
          setDeleteSavedSurveyModalOptions({ uuid: surveyID, isOpen: true });
        },
        share: (surveyID: number) => {
          setShareSavedSurveyModalOptions({ uuid: surveyID, isOpen: true });
        },
      }}
    />
  );

  const step0Content =
    initialRequest || isCreatingSurvey ? (
      <Surveys
        next={next()}
        frontendContent={frontendContent}
        selectedSurveyToEdit={selectedSurveyToEdit}
      />
    ) : (
      tableContent
    );

  return (
    <>
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
          <aside className="wfp--form-wizard__sidebar">
            <SurveyWizardStepNavigation />
          </aside>
          <Module className="survey-module">
            <SurveyWizardHeader />
            <ModulesProvider key={modulesContextKey}>
              <ModuleBody className="survey-content">
                {step === 0 && step0Content}
                {step === 1 && <Modules next={next()} />}
                {step === 2 && <Review next={next()} />}
                {step === 3 && <Generate next={next()} />}
              </ModuleBody>
            </ModulesProvider>
            <SurveyWizardFooter
              clearSavedSurveyFilters={() =>
                surveyTableRef.current?.clearFilters()
              }
              resetSurveyData={resetSurveyData}
              saveSurvey={saveSurvey}
            />
          </Module>
        </div>
      </Wrapper>
    </>
  );
}

function SurveyWizard() {
  const { t } = useTranslation();
  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const steps = [
    t("surveyWizard.steps.defineSurvey"),
    t("surveyWizard.steps.selectModules"),
    t("surveyWizard.steps.selectAdditionQuestions"),
    t("surveyWizard.steps.generatePublishSurvey"),
  ];
  const paths = ["survey", "modules", "review", "generate"];

  return (
    <SurveyWizardProvider
      steps={steps}
      paths={paths}
      initialIsCreatingSurvey={
        !(savedSurveys.data && savedSurveys.data.length > 0)
      }
    >
      <MainLayout
        title={t("surveyWizard.title")}
        subTitle={t("surveyWizard.subTitle")}
      >
        <SurveyWizardContent />
      </MainLayout>
    </SurveyWizardProvider>
  );
}

export default SurveyWizard;
