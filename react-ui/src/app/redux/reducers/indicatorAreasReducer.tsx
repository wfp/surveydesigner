import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { IndicatorAreaWithIndicators } from "../../types";
import { IndicatorArea } from "../../types/api";

interface IndicatorAreasState {
  isLoading: boolean;
  error: AxiosError | null;
  data: IndicatorAreaWithIndicators[] | null;
  selectedOptions: string[] | null;
}

const initialState: IndicatorAreasState = {
  isLoading: false,
  error: null,
  data: null,
  selectedOptions: null,
};

export const indicatorAreasSlice = createSlice({
  name: "indicatorAreas",
  initialState,
  reducers: {
    getIndicatorAreas: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setIndicatorAreas: (
      state,
      action: PayloadAction<IndicatorAreaWithIndicators[]>
    ) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setIndicatorAreasError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
    clearIndicatorAreas: (state) => ({
      ...state,
      isLoading: initialState.isLoading,
      error: initialState.error,
      data: initialState.data,
    }),
    setSelectedIndicatorAreaOptions: (
      state,
      action: PayloadAction<string[]>
    ) => ({
      ...state,
      selectedOptions: action.payload,
    }),
  },
});

export default indicatorAreasSlice.reducer;

export const indicatorAreasActions = indicatorAreasSlice.actions;
