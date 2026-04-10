import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import {
  ChoiceTranslation,
  SubQuestion,
  SurveyCategory,
  SurveyMode,
  SurveyTypes,
} from "../../types/api";

export interface OrganizationOption {
  id: number;
  value: number;
  label: string;
}

export interface SurveyFormState {
  name: string;
  organizations: OrganizationOption[];
  category?: SurveyCategory | null;
  type?: SurveyTypes | null;
  mode?: SurveyMode | null;
  attributes: number[];
  modules_order: number[];
  submodules: number[];
  indicators?: number[];
  indicator_areas_order: number[];
  indicators_order: Record<string, number[]>;
  sub_questions: SubQuestion[];
  languages: ChoiceTranslation[];
  submodules_order: number[];
}

const initialState: SurveyFormState = {
  name: "",
  organizations: [],
  category: null,
  type: null,
  mode: null,
  attributes: [],
  modules_order: [],
  submodules: [],
  sub_questions: [],
  indicators: [],
  indicator_areas_order: [],
  indicators_order: {},
  languages: [{ language: "en", language_display: "English" }],
  submodules_order: [],
};

export const surveyFormSlice = createSlice({
  name: "surveyForm",
  initialState,
  reducers: {
    setSurveyData: (
      state,
      action: PayloadAction<Partial<SurveyFormState>>
    ) => ({
      ...state,
      ...action.payload,
    }),
    resetSurveyData: (
      state,
      action: PayloadAction<Partial<SurveyFormState>>
    ) => ({
      ...initialState,
    }),
  },
});

export default surveyFormSlice.reducer;

export const surveyFormActions = surveyFormSlice.actions;
