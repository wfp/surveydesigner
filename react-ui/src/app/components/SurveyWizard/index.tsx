import React, { useState, useCallback, useEffect, useRef } from "react";

import {
  Button,
  Module,
  ModuleBody,
  ModuleFooter,
  ModuleHeader,
  Wrapper,
  Tooltip,
  InlineLoading,
} from "@wfp/react";

import { useNavigate, useLocation } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faArrowRight,
  faCircleQuestion,
  faFloppyDisk,
} from "@fortawesome/free-solid-svg-icons";

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
import { API, renderTooltipMarkdown } from "../../utils";
import { CheckboxState, PrevNextStepCallback } from "../../types";
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
import { StepNavigationWrapper } from "./UI/StepNavigationWrapper";
import { SurveyWizardHeader } from "./UI/SurveyWizardHeader";

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
  const [step, setStep] = useState(0);
  const [prvsStep, setPrvsStep] = useState(0);
  const [goToStep, setGoToStep] = useState(0);
  const [nextClickCount, setNextClickCount] = useState(0);
  const [isValidating, setIsValidating] = useState(false);
  const [selectedSurveyToEdit, setSelectedSurveyToEdit] =
    useState<SavedSurvey | null>(null);
  const [selectAllModules, setSelectAllModules] = useState<CheckboxState>({
    isChecked: false,
    run: false,
  });
  const [selectAllReview, setSelectAllReview] = useState<CheckboxState>({
    isChecked: false,
    run: false,
  });
  const [collapseAllModules, setCollapseAllModules] = useState<CheckboxState>({
    isChecked: false,
    run: false,
  });
  const [collapseAllIndicatorAreas, setCollapseAllIndicatorAreas] =
    useState<CheckboxState>({
      isChecked: false,
      run: false,
    });
  const [collapseAllReview, setCollapseAllReview] = useState<CheckboxState>({
    isChecked: false,
    run: false,
  });
  const [selectedModuleCounts, setSelectedModuleCounts] = useState<{
    moduleCount?: number;
    submoduleCount?: number;
  }>({
    moduleCount: 0,
    submoduleCount: 0,
  });

  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const initialRequest = useAppSelector(
    (state) => state.savedSurveys.initialRequest,
  );

  const [numberOfQuestionsToBeGenerated, setNumberOfQuestionsToBeGenerated] =
    useState(0);
  const navigate = useNavigate();
  const location = useLocation();
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
  const paths = ["survey", "modules", "review", "generate"];

  const handleStepClick = useCallback(
    (targetIndex: number) => {
      if (targetIndex === step) return;
      if (targetIndex > step && step === 1) {
        setIsValidating(true);
      } else {
        setIsValidating(false);
      }

      setGoToStep(targetIndex);
    },
    [step],
  );

  useEffect(() => {
    // If a copiedSurvey is present in navigation state, use it directly
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
  const step3Tooltip = renderTooltipMarkdown(frontendContent, "step3Tooltip");
  const step1Tooltip = renderTooltipMarkdown(frontendContent, "step1Tooltip");
  const stepTooltips = [step1Tooltip, null, step3Tooltip, null];

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
    [goToStep, step],
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

  const sidebar = (
    <StepNavigationWrapper
      steps={steps}
      currentStep={step}
      onStepClick={handleStepClick}
    />
  );
  const showModulesCount = step === 1 && !!selectedModuleCounts.submoduleCount;
  const showQuestionsCount = step === 2 && !!numberOfQuestionsToBeGenerated;

  const [isCreatingSurvey, setIsCreatingSurvey] = useState(
    !(savedSurveys.data && savedSurveys.data.length > 0),
  );

  function resetSurveyData() {
    dispatch(fetchSavedSurveys({}));
    setGoToStep(0);
    setIsCreatingSurvey(false);
    setSelectedSurveyToEdit(null);
    dispatch(surveyFormActions.resetSurveyData({}));
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

  const renderPreviousButton = () => {
    const shouldShowButton =
      step > 0 || (isCreatingSurvey && savedSurveys.data);
    const hasSavedSurveys = savedSurveys.data && savedSurveys.data.length > 0;
    // If still loading savedSurveys.data
    if (isCreatingSurvey && !savedSurveys.data) {
      return <InlineLoading description="Loading saved surveys..." />;
    }

    // If the button shouldn't be shown
    if (!shouldShowButton) {
      return null;
    }
    const isDisabled = step === 0 && !hasSavedSurveys;

    const buttonContent = (
      <Button
        kind="secondary"
        className="wfp--form-controls__prev wfp--btn wfp--btn--secondary"
        disabled={isDisabled}
        onClick={() => {
          if (step > 0) {
            setGoToStep(step - 1);
          } else {
            setIsCreatingSurvey(false);
            resetSurveyData();
          }
        }}
      >
        {step > 0 ? t("actions.previous") : t("surveyWizard.savedSurveys")}
        <FontAwesomeIcon icon={faArrowLeft} className="wfp--btn__icon" />
      </Button>
    );
    if (isDisabled) {
      return (
        <Tooltip
          className="custom-tooltip"
          createRefWrapper
          content={"There are no saved surveys"}
          dark
          placement="top-end"
          trigger="hover"
        >
          {buttonContent}
        </Tooltip>
      );
    }

    return buttonContent;
  };
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
              <SurveyWizardHeader
                step={step}
                stepsCount={stepsCount}
                steps={steps}
                stepTooltips={stepTooltips}
                showModulesCount={showModulesCount}
                showQuestionsCount={showQuestionsCount}
                selectedModuleCounts={selectedModuleCounts}
                numberOfQuestionsToBeGenerated={numberOfQuestionsToBeGenerated}
                selectAllModules={selectAllModules}
                setSelectAllModules={setSelectAllModules}
                collapseAllModules={collapseAllModules}
                setCollapseAllModules={setCollapseAllModules}
                collapseAllIndicatorAreas={collapseAllIndicatorAreas}
                setCollapseAllIndicatorAreas={setCollapseAllIndicatorAreas}
                selectAllReview={selectAllReview}
                setSelectAllReview={setSelectAllReview}
                collapseAllReview={collapseAllReview}
                setCollapseAllReview={setCollapseAllReview}
              />
            </ModuleHeader>
            <ModulesProvider>
              <ModuleBody className="survey-content">
                {step === 0 && step0Content}
                {step === 1 && (
                  <Modules
                    next={next()}
                    selectAll={selectAllModules}
                    setSelectAll={setSelectAllModules}
                    collapseAllModules={collapseAllModules}
                    setCollapseAllModules={setCollapseAllModules}
                    collapseAllIndicatorAreas={collapseAllIndicatorAreas}
                    setCollapseAllIndicatorAreas={setCollapseAllIndicatorAreas}
                    selectedSurveyToEdit={selectedSurveyToEdit}
                    {...{
                      prvsStep,
                      step,
                      setSelectedModuleCounts,
                    }}
                    setIsValidating={setIsValidating}
                  />
                )}
                {step === 2 && (
                  <Review
                    next={next()}
                    selectAll={selectAllReview}
                    setSelectAll={setSelectAllReview}
                    collapseAll={collapseAllReview}
                    setCollapseAll={setCollapseAllReview}
                    selectedSurveyToEdit={selectedSurveyToEdit}
                    {...{
                      numberOfQuestionsToBeGenerated,
                      setNumberOfQuestionsToBeGenerated,
                    }}
                  />
                )}
                {step === 3 && <Generate next={next()} />}
              </ModuleBody>
            </ModulesProvider>
            <ModuleFooter>
              <div className="wfp--form-controls">
                <div>{renderPreviousButton()}</div>
                <div>
                  {isCreatingSurvey && step < stepsCount - 1 ? (
                    <Button
                      kind="secondary"
                      className="wfp--form-controls__next wfp--btn wfp--btn--secondary"
                      disabled={step === 1 && isValidating}
                      onClick={() => {
                        if (step === 1) {
                          setIsValidating(true);
                        }
                        setGoToStep(step + 1);
                        setNextClickCount(nextClickCount + 1);
                      }}
                    >
                      {t("actions.next")}
                      <FontAwesomeIcon icon={faArrowRight} className="wfp--btn__icon" />
                    </Button>
                  ) : (
                    step === 0 && (
                      <Button
                        kind="secondary"
                        onClick={() => {
                          setIsCreatingSurvey(true);
                          if (
                            surveyTableRef &&
                            surveyTableRef.current &&
                            surveyTableRef.current !== null
                          )
                            surveyTableRef.current.clearFilters();
                        }}
                      >
                        {t("surveyWizard.createSurvey")}
                      </Button>
                    )
                  )}
                </div>
                {step === stepsCount - 1 && (
                  <div>
                    <Button
                      kind="secondary"
                      className="wfp--form-controls__next"
                      onClick={() => {
                        saveSurvey();
                      }}
                    >
                      {t("actions.save")}
                      <FontAwesomeIcon icon={faFloppyDisk} className="wfp--btn__icon" />
                    </Button>
                  </div>
                )}
              </div>
            </ModuleFooter>
          </Module>
        </div>
      </Wrapper>
    </MainLayout>
  );
}

export default SurveyWizard;
