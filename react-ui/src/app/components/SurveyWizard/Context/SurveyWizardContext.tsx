import React, { createContext, useContext, useState, useCallback, useRef, useEffect, ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../../redux/store";
import { CheckboxState, PrevNextStepCallback } from "../../../types";
import { SavedSurvey, SurveyCategory, SurveyMode, SurveyTypes } from "../../../types/api";
import { fetchSavedSurveys, postSavedSurvey, putSavedSurvey } from "../../../redux/actions/savedSurveysActions";
import { savedSurveysActions } from "../../../redux/reducers/savedSurveysReducer";
import { surveyFormActions } from "../../../redux/reducers/surveyFormReducer";
import { modulesActions } from "../../../redux/reducers/modulesReducer";
import { PayloadAction } from "@reduxjs/toolkit";

interface SurveyWizardContextType {
  // State
  step: number;
  goToStep: number;
  isValidating: boolean;
  selectedSurveyToEdit: SavedSurvey | null;
  selectAllModules: CheckboxState;
  collapseAllModules: CheckboxState;
  collapseAllIndicatorAreas: CheckboxState;
  selectAllReview: CheckboxState;
  collapseAllReview: CheckboxState;
  selectedModuleCounts: { moduleCount?: number; submoduleCount?: number };
  numberOfQuestionsToBeGenerated: number;
  isCreatingSurvey: boolean;
  prvsStep: number;
  stepsCount: number;
  savedSurveys: any;
  steps: string[];
  stepTooltips: (React.ReactElement | null)[];
  
  // Setters/Handlers
  setStep: (step: number) => void;
  setGoToStep: (step: number) => void;
  setIsValidating: (isValidating: boolean) => void;
  setSelectedSurveyToEdit: (survey: SavedSurvey | null) => void;
  setSelectAllModules: (state: CheckboxState) => void;
  setCollapseAllModules: (state: CheckboxState) => void;
  setCollapseAllIndicatorAreas: (state: CheckboxState) => void;
  setSelectAllReview: (state: CheckboxState) => void;
  setCollapseAllReview: (state: CheckboxState) => void;
  setSelectedModuleCounts: (counts: { moduleCount?: number; submoduleCount?: number }) => void;
  setNumberOfQuestionsToBeGenerated: (count: number) => void;
  setIsCreatingSurvey: (isCreating: boolean) => void;
  
  handleStepClick: (targetIndex: number) => void;
  next: () => PrevNextStepCallback;
  saveSurvey: () => Promise<void>;
  resetSurveyData: () => void;
}

const SurveyWizardContext = createContext<SurveyWizardContextType | undefined>(undefined);

export const useSurveyWizard = () => {
  const context = useContext(SurveyWizardContext);
  if (!context) {
    throw new Error("useSurveyWizard must be used within a SurveyWizardProvider");
  }
  return context;
};

interface SurveyWizardProviderProps {
  children: ReactNode;
}

export const SurveyWizardProvider = ({ children }: SurveyWizardProviderProps) => {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const savedSurveys = useAppSelector((state) => state.savedSurveys);

  const [step, setStep] = useState(0);
  const [prvsStep, setPrvsStep] = useState(0);
  const [goToStep, setGoToStep] = useState(0);
  const [nextClickCount, setNextClickCount] = useState(0);
  const [isValidating, setIsValidating] = useState(false);
  const [selectedSurveyToEdit, setSelectedSurveyToEdit] = useState<SavedSurvey | null>(null);
  const [isCreatingSurvey, setIsCreatingSurvey] = useState(!(savedSurveys.data && savedSurveys.data.length > 0));

  const [selectAllModules, setSelectAllModules] = useState<CheckboxState>({ isChecked: false, run: false });
  const [selectAllReview, setSelectAllReview] = useState<CheckboxState>({ isChecked: false, run: false });
  const [collapseAllModules, setCollapseAllModules] = useState<CheckboxState>({ isChecked: false, run: false });
  const [collapseAllIndicatorAreas, setCollapseAllIndicatorAreas] = useState<CheckboxState>({ isChecked: false, run: false });
  const [collapseAllReview, setCollapseAllReview] = useState<CheckboxState>({ isChecked: false, run: false });
  
  const [selectedModuleCounts, setSelectedModuleCounts] = useState<{ moduleCount?: number; submoduleCount?: number }>({
    moduleCount: 0,
    submoduleCount: 0,
  });
  const [numberOfQuestionsToBeGenerated, setNumberOfQuestionsToBeGenerated] = useState(0);

  const paths = ["survey", "modules", "review", "generate"];

  const handleStepClick = useCallback((targetIndex: number) => {
    if (targetIndex === step) return;
    if (targetIndex > step && step === 1) {
      setIsValidating(true);
    } else {
      setIsValidating(false);
    }
    setGoToStep(targetIndex);
  }, [step]);

  const next = useCallback((): PrevNextStepCallback => (nextCallback, prevCallback) => {
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
  }, [goToStep, step, navigate, paths]);

  const resetSurveyData = useCallback(() => {
    dispatch(fetchSavedSurveys({}));
    setGoToStep(0);
    setIsCreatingSurvey(false);
    setSelectedSurveyToEdit(null);
    dispatch(surveyFormActions.resetSurveyData({}));
  }, [dispatch]);

  const isSavedSurveyActionSuccess = useCallback((res: PayloadAction<any>, actionType: string) => {
    if (res.type === actionType) {
      resetSurveyData();
    }
  }, [resetSurveyData]);

  const saveSurvey = async () => {
    if (selectedSurveyToEdit && selectedSurveyToEdit.uuid) {
      dispatch(putSavedSurvey({ ...surveyForm, uuid: selectedSurveyToEdit.uuid }))
        .then((res) => {
          isSavedSurveyActionSuccess(res, "saved_surveys/PUT_SAVEDSURVEYS/fulfilled");
        });
    } else {
      dispatch(postSavedSurvey(surveyForm)).then((res) => {
        isSavedSurveyActionSuccess(res, "saved_surveys/POST_SAVEDSURVEYS/fulfilled");
      });
    }
  };

  const steps = [t("steps.survey"), t("steps.modules"), t("steps.review"), t("steps.generate")];
  const stepsCount = paths.length; // 4
  const stepTooltips = [null, null, null, null]; // Add tooltips if needed

  const value = React.useMemo(() => ({
    step,
    goToStep,
    isValidating,
    selectedSurveyToEdit,
    selectAllModules,
    collapseAllModules,
    collapseAllIndicatorAreas,
    selectAllReview,
    collapseAllReview,
    selectedModuleCounts,
    numberOfQuestionsToBeGenerated,
    isCreatingSurvey,
    prvsStep,
    stepsCount,
    savedSurveys,
    steps,
    stepTooltips,
    setStep,
    setGoToStep,
    setIsValidating,
    setSelectedSurveyToEdit,
    setSelectAllModules,
    setCollapseAllModules,
    setCollapseAllIndicatorAreas,
    setSelectAllReview,
    setCollapseAllReview,
    setSelectedModuleCounts,
    setNumberOfQuestionsToBeGenerated,
    setIsCreatingSurvey,
    handleStepClick,
    next,
    saveSurvey,
    resetSurveyData,
  }), [
    step, goToStep, isValidating, selectedSurveyToEdit, selectAllModules,
    collapseAllModules, collapseAllIndicatorAreas, selectAllReview,
    collapseAllReview, selectedModuleCounts, numberOfQuestionsToBeGenerated,
    isCreatingSurvey, prvsStep, stepsCount, savedSurveys, steps, stepTooltips,
    handleStepClick, next, saveSurvey, resetSurveyData
  ]);

  return <SurveyWizardContext.Provider value={value}>{children}</SurveyWizardContext.Provider>;
};
