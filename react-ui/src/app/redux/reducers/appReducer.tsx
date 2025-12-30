import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  isLoading: boolean;
}

const initialState: AppState = {
  isLoading: false,
};

export const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    isLoading: (state, action: PayloadAction<boolean>) => ({
      ...state,
      error: null,
      isLoading: action.payload,
    }),
  },
});

export default appSlice.reducer;

export const appActions = appSlice.actions;
