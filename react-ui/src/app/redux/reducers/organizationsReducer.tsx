import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { Organization } from "../../types/api";

interface OrganizationsState {
  isLoading: boolean;
  error: AxiosError | null;
  data: Organization[] | null;
}

const initialState: OrganizationsState = {
  isLoading: false,
  error: null,
  data: null,
};

export const organizationsSlice = createSlice({
  name: "organizations",
  initialState,
  reducers: {
    getOrganizations: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setOrganizations: (state, action: PayloadAction<Organization[]>) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setOrganizationsError: (state, action: PayloadAction<AxiosError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
  },
});

export default organizationsSlice.reducer;

export const organizationsActions = organizationsSlice.actions;
