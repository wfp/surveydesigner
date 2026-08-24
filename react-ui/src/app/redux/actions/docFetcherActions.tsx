import { Cookies } from "react-cookie";
import { API } from "../../utils";
import { createAppAsyncThunk } from "../store";
import { docFetcherActions } from "../reducers/docFetcherReducer";
import { notificationsActions } from "../reducers/notificationReducer";
import { renderApiErrorMessage } from "../../utils/apiError";

interface ClearJobPayload {
  isCancelled?: boolean;
}

export const clearJob = createAppAsyncThunk<void, ClearJobPayload | undefined>(
  "docFetcher/CLEAR_JOB",
  (payload, { dispatch, getState }) => {
    const { isCancelled = false } = payload ?? {};
    if (isCancelled) {
      const { docFetcher } = getState();
      const cookies = new Cookies();
      const csrfToken = cookies.get("csrftoken");
      API.get("/generate-doc/", {
        headers: {
          "X-CSRFToken": csrfToken,
        },
        params: {
          jobId: docFetcher.jobId,
          cancelJob: true,
        },
      })
        .then((res) => {
          dispatch(
            notificationsActions.setSuccessNotification({
              msg: res.data.detail,
            }),
          );
          dispatch(docFetcherActions.clearJobId());
        })
        .catch((err) => {
          dispatch(
            notificationsActions.setErrorNotification({
              msg: renderApiErrorMessage(
                err,
                "The Word generation job could not be cancelled.",
              ),
            }),
          );
        });
    } else {
      dispatch(docFetcherActions.clearJobId());
    }
  },
);
