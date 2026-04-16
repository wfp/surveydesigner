import axios from "axios";
import { createAppAsyncThunk } from "../store";
import { appActions } from "../reducers/appReducer";
import { authActions } from "../reducers/authReducer";
import { API } from "../../utils";

export const logout = createAppAsyncThunk(
  "auth/LOGOUT",
  (_, { dispatch, getState }) => {
    dispatch(authActions.clearData);
    window.location.href = `${import.meta.env.VITE_APP_API_ENDPOINT}/auth/logout/`;
  }
);

export const loadUserData = createAppAsyncThunk(
  "auth/LOAD_USER_DATA",
  async (_, { dispatch }) => {
    dispatch(appActions.isLoading(true));
    try {
      const response = await API.get("/accounts/user/", { withCredentials: true });
      if (response.status !== 200) {
        dispatch(authActions.clearData());
      } else {
        const user = response.data;
        dispatch(authActions.loadUser({ is_logged: true, user }));
      }
    } catch {
      dispatch(authActions.clearData());
    } finally {
      dispatch(appActions.isLoading(false));
    }
  }
);
