import { Organization } from "../../types/api";
import { API } from "../../utils";
import { organizationsActions } from "../reducers/organizationsReducer";
import { createAppAsyncThunk } from "../store";

export const fetchOrganizations = createAppAsyncThunk(
  "organizations/FETCH_ORGANIZATIONS",
  (_, { dispatch, getState }) => {
    dispatch(organizationsActions.getOrganizations());
    API.get<Organization[]>("/organizations/")
      .then((res) => {
        dispatch(organizationsActions.setOrganizations(res.data));
      })
      .catch((err) => {
        dispatch(organizationsActions.setOrganizationsError(err));
      });
  }
);
