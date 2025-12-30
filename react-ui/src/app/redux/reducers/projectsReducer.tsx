import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { ApiError } from "../../types";
import { UserProjectListAPIResponse } from "../../types/api";

interface ProjectsState {
  isLoading: boolean;
  error: ApiError | null;
  data: UserProjectListAPIResponse[] | null;
}

const initialState: ProjectsState = {
  isLoading: false,
  error: null,
  data: null,
};

export const projectsSlice = createSlice({
  name: "projects",
  initialState,
  reducers: {
    getProjects: (state) => ({
      ...state,
      data: null,
      error: null,
      isLoading: true,
    }),
    setProjects: (
      state,
      action: PayloadAction<UserProjectListAPIResponse[]>
    ) => ({
      ...state,
      data: action.payload,
      error: null,
      isLoading: false,
    }),
    setProjectsError: (state, action: PayloadAction<ApiError>) => ({
      ...state,
      data: null,
      error: action.payload,
      isLoading: false,
    }),
  },
});

export default projectsSlice.reducer;

export const projectsActions = projectsSlice.actions;
