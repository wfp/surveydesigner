import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { SavedSurvey } from "../../types/api";

interface SavedSurveyState {
  isLoading: boolean;
  error: AxiosError | null;
  data: SavedSurvey[] | null;
  detail: SavedSurvey | null;
  initialRequest: boolean;
}

const initialState: SavedSurveyState = {
  isLoading: false,
  error: null,
  data: null,
  detail: null,
  initialRequest: true,
};

export const savedSurveySlice = createSlice({
  name: "saved_surveys",
  initialState,
  reducers: {
    getSavedSurveys: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setSavedSurveys: (state, action: PayloadAction<SavedSurvey[]>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setSavedSurveysError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
    completeInitialRequest: (state) => {
      state.initialRequest = false;
    },
    setSavedSurveyDetail: (state, action: PayloadAction<SavedSurvey>) => ({
      ...state,
      detail: action.payload,
      error: null,
      isLoading: false,
    }),
    clearSavedSurveyDetail: (state) => ({
      ...state,
      detail: null,
      error: null,
      isLoading: false,
    }),
  },
});

export default savedSurveySlice.reducer;

export const savedSurveysActions = savedSurveySlice.actions;
