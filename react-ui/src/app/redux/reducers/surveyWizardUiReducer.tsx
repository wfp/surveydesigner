import { PayloadAction, createSlice } from "@reduxjs/toolkit";
import { CheckboxState } from "../../types";
import { SavedSurvey } from "../../types/api";
import { RootState } from "../store";

type SurveyWizardUiState = {
  step: number;
  prvsStep: number;
  goToStep: number;
  isValidating: boolean;
  isCreatingSurvey: boolean;
  selectAllModules: CheckboxState;
  selectAllReview: CheckboxState;
  collapseAllModules: CheckboxState;
  collapseAllIndicatorAreas: CheckboxState;
  collapseAllReview: CheckboxState;
  selectedModuleCounts: {
    moduleCount?: number;
    submoduleCount?: number;
  };
  numberOfQuestionsToBeGenerated: number;
  selectedSurveyToEdit: SavedSurvey | null;
};

const uncheckedState: CheckboxState = {
  isChecked: false,
  run: false,
};

const initialState: SurveyWizardUiState = {
  step: 0,
  prvsStep: 0,
  goToStep: 0,
  isValidating: false,
  isCreatingSurvey: true,
  selectAllModules: uncheckedState,
  selectAllReview: uncheckedState,
  collapseAllModules: uncheckedState,
  collapseAllIndicatorAreas: uncheckedState,
  collapseAllReview: uncheckedState,
  selectedModuleCounts: {
    moduleCount: 0,
    submoduleCount: 0,
  },
  numberOfQuestionsToBeGenerated: 0,
  selectedSurveyToEdit: null,
};

const surveyWizardUiSlice = createSlice({
  name: "surveyWizardUi",
  initialState,
  reducers: {
    setStep: (state, action: PayloadAction<number>) => ({
      ...state,
      step: action.payload,
    }),
    setPrvsStep: (state, action: PayloadAction<number>) => ({
      ...state,
      prvsStep: action.payload,
    }),
    setGoToStep: (state, action: PayloadAction<number>) => ({
      ...state,
      goToStep: action.payload,
    }),
    goToStepSafe: (state, action: PayloadAction<number>) => ({
      ...state,
      goToStep: action.payload === state.step ? state.goToStep : action.payload,
      isValidating:
        action.payload > state.step && state.step === 1
          ? true
          : action.payload === state.step
            ? state.isValidating
            : false,
    }),
    goNext: (state) => ({
      ...state,
      goToStep: state.step + 1,
      isValidating: state.step === 1 ? true : state.isValidating,
    }),
    goPrevious: (state) => ({
      ...state,
      goToStep: state.step > 0 ? state.step - 1 : 0,
    }),
    setIsValidating: (state, action: PayloadAction<boolean>) => ({
      ...state,
      isValidating: action.payload,
    }),
    setIsCreatingSurvey: (state, action: PayloadAction<boolean>) => ({
      ...state,
      isCreatingSurvey: action.payload,
    }),
    setSelectAllModules: (state, action: PayloadAction<CheckboxState>) => ({
      ...state,
      selectAllModules: action.payload,
    }),
    setSelectAllReview: (state, action: PayloadAction<CheckboxState>) => ({
      ...state,
      selectAllReview: action.payload,
    }),
    setCollapseAllModules: (state, action: PayloadAction<CheckboxState>) => ({
      ...state,
      collapseAllModules: action.payload,
    }),
    setCollapseAllIndicatorAreas: (
      state,
      action: PayloadAction<CheckboxState>,
    ) => ({
      ...state,
      collapseAllIndicatorAreas: action.payload,
    }),
    setCollapseAllReview: (state, action: PayloadAction<CheckboxState>) => ({
      ...state,
      collapseAllReview: action.payload,
    }),
    setSelectedModuleCounts: (
      state,
      action: PayloadAction<{ moduleCount?: number; submoduleCount?: number }>,
    ) => ({
      ...state,
      selectedModuleCounts: action.payload,
    }),
    setNumberOfQuestionsToBeGenerated: (
      state,
      action: PayloadAction<number>,
    ) => ({
      ...state,
      numberOfQuestionsToBeGenerated: action.payload,
    }),
    setSelectedSurveyToEdit: (
      state,
      action: PayloadAction<SavedSurvey | null>,
    ) => ({
      ...state,
      selectedSurveyToEdit: action.payload,
    }),
    resetSurveyWizardUi: () => initialState,
    resetWizardSession: (state) => ({
      ...initialState,
      isCreatingSurvey: state.isCreatingSurvey,
    }),
  },
});

export const surveyWizardUiActions = surveyWizardUiSlice.actions;
export default surveyWizardUiSlice.reducer;
export const selectSurveyWizardUi = (state: RootState) => state.surveyWizardUi;
export const selectWizardStep = (state: RootState) => state.surveyWizardUi.step;
export const selectWizardCanGoNext = (state: RootState) =>
  state.surveyWizardUi.isCreatingSurvey && state.surveyWizardUi.step < 3;

