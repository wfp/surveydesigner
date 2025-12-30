import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { Indicator } from "../../types/api";

interface IndicatorsState {
  isLoading: boolean;
  error: AxiosError | null;
  data: Indicator[] | null;
  selectedOptions: string[] | null;
}

const initialState: IndicatorsState = {
  isLoading: false,
  error: null,
  data: null,
  selectedOptions: null,
};

export const indicatorsSlice = createSlice({
  name: "indicators",
  initialState,
  reducers: {
    getIndicators: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setIndicators: (state, action: PayloadAction<Indicator[]>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setIndicatorsError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
    clearIndicators: (state) => ({
      ...state,
      isLoading: initialState.isLoading,
      error: initialState.error,
      data: initialState.data,
    }),
    setSelectedIndicatorOptions: (state, action: PayloadAction<string[]>) => ({
      ...state,
      selectedOptions: action.payload,
    }),
  },
});

export default indicatorsSlice.reducer;

export const indicatorsActions = indicatorsSlice.actions;
