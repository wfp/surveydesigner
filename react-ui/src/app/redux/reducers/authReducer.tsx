import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { UserDetail } from "../../types/api";

interface AuthState {
  is_logged: boolean;
  user?: UserDetail;
}

const initialState: AuthState = {
  is_logged: false,
  user: undefined,
};

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    loadUser: (state, action: PayloadAction<Partial<AuthState>>) => ({
      ...state,
      ...action.payload,
    }),
    clearData: (state) => ({ ...state, ...initialState }),
  },
});

export default authSlice.reducer;

export const authActions = authSlice.actions;
