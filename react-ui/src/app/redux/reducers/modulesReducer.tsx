import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { Module } from "../../types/api";

interface ModulesState {
  isLoading: boolean;
  error: AxiosError | null;
  data: Module[] | null;
}

const initialState: ModulesState = {
  isLoading: false,
  error: null,
  data: null,
};

export const modulesSlice = createSlice({
  name: "modules",
  initialState,
  reducers: {
    getModules: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setModules: (state, action: PayloadAction<Module[]>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setModulesError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
    clearModules: (state) => ({
      ...state,
      ...initialState,
    }),
  },
});

export default modulesSlice.reducer;

export const modulesActions = modulesSlice.actions;
