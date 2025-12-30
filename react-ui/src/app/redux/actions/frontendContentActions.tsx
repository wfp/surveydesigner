import { FrontendContent } from "../../types/api";
import { API } from "../../utils";
import { frontendContentActions } from "../reducers/frontendContentReducer";
import { createAppAsyncThunk } from "../store";

export const fetchFrontendContent = createAppAsyncThunk(
  "frontendContent/FETCH_FRONTEND_CONTENT",
  (_, { dispatch, getState }) => {
    dispatch(frontendContentActions.getFrontendContent());
    API.get<FrontendContent[]>("/frontend-content/")
      .then((res) => {
        dispatch(frontendContentActions.setFrontendContent(res.data));
      })
      .catch((err) => {
        dispatch(frontendContentActions.setFrontendContentError(err));
      });
  }
);
