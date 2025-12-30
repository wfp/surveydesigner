import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { FrontendContent } from "../../types/api";

interface FrontendContentState {
  isLoading: boolean;
  error: AxiosError | null;
  data: FrontendContent[] | null;
  selectedOptions: string[] | null;
}

const initialState: FrontendContentState = {
  isLoading: false,
  error: null,
  data: null,
  selectedOptions: null,
};

export const frontendContentSlice = createSlice({
  name: "frontendContent",
  initialState,
  reducers: {
    getFrontendContent: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setFrontendContent: (state, action: PayloadAction<FrontendContent[]>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setFrontendContentError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
  },
});

export default frontendContentSlice.reducer;

export const frontendContentActions = frontendContentSlice.actions;
