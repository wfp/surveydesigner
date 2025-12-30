import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { Surveys } from "../../types/api";

interface SurveysState {
  isLoading: boolean;
  error: AxiosError | null;
  data: Surveys | null;
}

const initialState: SurveysState = {
  isLoading: false,
  error: null,
  data: null,
};

export const surveysSlice = createSlice({
  name: "surveys",
  initialState,
  reducers: {
    getSurveys: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setSurveys: (state, action: PayloadAction<Surveys>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setSurveysError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
  },
});

export default surveysSlice.reducer;

export const surveysActions = surveysSlice.actions;
