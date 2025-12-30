import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { SubmoduleWithQuestions } from "../../types/api";

export interface SubmodulesState {
  isLoading: boolean;
  error: AxiosError | null;
  data: SubmoduleWithQuestions[] | null;
  selectedOptions: number[] | null;
}

const initialState: SubmodulesState = {
  isLoading: false,
  error: null,
  data: null,
  selectedOptions: null,
};

export const submodulesSlice = createSlice({
  name: "submodules",
  initialState,
  reducers: {
    getSubmodules: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setSubmodules: (
      state,
      action: PayloadAction<SubmoduleWithQuestions[]>
    ) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setSubmodulesError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
    clearSubmodules: (state) => ({
      ...state,
      isLoading: initialState.isLoading,
      error: initialState.error,
      data: initialState.data,
    }),
    setSelectedSubmodulesOptions: (state, action: PayloadAction<number[]>) => ({
      ...state,
      selectedOptions: action.payload,
    }),
  },
});

export default submodulesSlice.reducer;

export const submodulesActions = submodulesSlice.actions;
