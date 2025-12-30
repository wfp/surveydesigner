import { UserProjectListAPIResponse } from "../../types/api";
import { API } from "../../utils";
import { projectsActions } from "../reducers/projectsReducer";
import { createAppAsyncThunk } from "../store";

export const fetchProjects = createAppAsyncThunk<void, number>(
  "projects/FETCH_PROJECTS",
  (siteId, { dispatch, getState }) => {
    dispatch(projectsActions.getProjects());

    API.get<UserProjectListAPIResponse[]>("/accounts/projects/", {
      params: {
        site: siteId,
      },
    })
      .then((res) => {
        dispatch(projectsActions.setProjects(res.data));
      })
      .catch((err) => {
        dispatch(projectsActions.setProjectsError(err));
      });
  }
);
