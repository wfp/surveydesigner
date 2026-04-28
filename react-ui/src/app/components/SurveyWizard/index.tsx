import React, { useEffect, useRef, useState } from "react";
import {
  Module,
  ModuleBody,
  ModuleHeader,
  Wrapper,
} from "@wfp/react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import MainLayout from "../Layout";
import Modules from "../Modules";
import Surveys from "../Surveys";
import Review from "../Review";
import Generate from "../Generate";
import DocFetcher from "../DocFetcher";
import { ModulesProvider } from "../../contexts/ModulesContext";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { renderTooltipMarkdown } from "../../utils";
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
import { SurveyWizardFooter } from "./UI/SurveyWizardFooter";
import { SurveyWizardProvider, useSurveyWizard } from "./Context/SurveyWizardContext";
import { fetchSavedSurveys } from "../../redux/actions/savedSurveysActions";
import { savedSurveysActions } from "../../redux/reducers/savedSurveysReducer";
import { SavedSurvey } from "../../types/api";
import { fetchFrontendContent } from "../../redux/actions/frontendContentActions";
import SurveyTable from "../SurveyTable";

function SurveyWizardContent() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const location = useLocation();
  const {
    step,
    setStep,
    isValidating,
    setIsValidating,
    selectedSurveyToEdit,
    setSelectedSurveyToEdit,
    setIsCreatingSurvey,
    isCreatingSurvey,
    handleStepClick,
    next,
    resetSurveyData,
    setGoToStep,
    selectedModuleCounts,
    numberOfQuestionsToBeGenerated,
    prvsStep,
  } = useSurveyWizard();

  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const initialRequest = useAppSelector((state) => state.savedSurveys.initialRequest);

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

  const state = (location.state || {}) as {
    surveyId?: number | string;
    copiedSurvey?: any;
  };

  const stepsCount = 4;
  const steps = [
    t("surveyWizard.steps.defineSurvey"),
    t("surveyWizard.steps.selectModules"),
    t("surveyWizard.steps.selectAdditionQuestions"),
    t("surveyWizard.steps.generatePublishSurvey"),
  ];

  useEffect(() => {
    if (state && state.copiedSurvey) {
      setSelectedSurveyToEdit(state.copiedSurvey);
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
              setIsCreatingSurvey(true);
            }
          }
        }
      });
      dispatch(savedSurveysActions.completeInitialRequest());
    }
  }, []);

  useEffect(() => {
    if (!frontendContent) {
      dispatch(fetchFrontendContent());
    }
  }, []);

  const step3Tooltip = renderTooltipMarkdown(frontendContent, "step3Tooltip");
  const step1Tooltip = renderTooltipMarkdown(frontendContent, "step1Tooltip");
  const stepTooltips = [step1Tooltip, null, step3Tooltip, null];

  const sidebar = (
    <StepNavigationWrapper
      steps={steps}
      currentStep={step}
      onStepClick={handleStepClick}
    />
  );
  const showModulesCount = step === 1 && !!selectedModuleCounts.submoduleCount;
  const showQuestionsCount = step === 2 && !!numberOfQuestionsToBeGenerated;

  const prevValues = useRef({
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
      if (JSON.stringify(prevValues.current) !== JSON.stringify(currentValues)) {
        dispatch(modulesActions.clearModules());
        prevValues.current = currentValues as any;
      }
    }
  }, [step, selectedSurveyToEdit, currentValues, dispatch]);

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
                newSurvey[key] = (value as any).name || (value as any).label;
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
                    (savedSurvey: SavedSurvey) => savedSurvey.uuid === surveyID,
                  )
                : null;
            setIsCreatingSurvey(true);
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
    </div>
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
    <MainLayout
      title={t("surveyWizard.title")}
      subTitle={t("surveyWizard.subTitle")}
    >
      <DocFetcher />
      <DeleteSavedSurveyModal
        deleteSavedSurveyModalOptions={deleteSavedSurveyModalOptions}
        isSavedSurveyActionSuccess={() => {}}
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
                {step === 1 && <Modules />}
                {step === 2 && <Review />}
                {step === 3 && <Generate />}
              </ModuleBody>
            </ModulesProvider>
            <SurveyWizardFooter />
          </Module>
        </div>
      </Wrapper>
    </MainLayout>
  );
}

function SurveyWizard() {
  return (
    <SurveyWizardProvider>
      <SurveyWizardContent />
    </SurveyWizardProvider>
  );
}

export default SurveyWizard;
