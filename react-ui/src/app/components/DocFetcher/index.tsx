import React, { useEffect, useState } from "react";
import { Cookies } from "react-cookie";
import {
  docFetcherActions,
  DocFetcherState,
} from "../../redux/reducers/docFetcherReducer";
import { notificationsActions } from "../../redux/reducers/notificationReducer";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { clearJob } from "../../redux/actions/docFetcherActions";
import { API } from "../../utils";
import { downloadFile } from "../../utils/download";

function DocFetcher() {
  const [job, setJob] = useState<(DocFetcherState & { doc: string }) | null>(
    null
  );
  const [intervalId, setIntervalId] = useState<NodeJS.Timer | undefined>(
    undefined
  );
  const { jobId } = useAppSelector((state) => state.docFetcher);

  const dispatch = useAppDispatch();

  const fetchDoc = () => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    API.get("/generate-doc/", {
      headers: {
        "X-CSRFToken": csrfToken,
      },
      params: {
        jobId,
      },
    })
      .then((res) => {
        const {
          status: statusRes,
          position: positionRes,
          jobId: jobIdRes,
          doc,
        } = res.data;
        setJob({
          status: statusRes,
          position: positionRes,
          jobId: jobIdRes,
          doc,
        });
      })
      .catch((err) => {
        dispatch(
          notificationsActions.setErrorNotification({
            msg: `${
              err.response.data.message
                ? err.response.data.message
                : err.message
            }`,
          })
        );
        dispatch(clearJob());
      });
  };

  const downloadDoc = () => {
    const timestamp = new Date().getTime().toString();
    if (!job) return;

    API.get(job.doc, {
      responseType: "blob",
      baseURL: "",
    })
      .then((res) => {
        downloadFile(
          res,
          timestamp,
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "docx"
        );
      })
      .catch((err) => {
        const errorMessage =
          err.response?.data?.message ||
          err.message ||
          "Unknown error occurred";
        dispatch(
          notificationsActions.setErrorNotification({
            msg: `Error: ${errorMessage}`,
          })
        );
        dispatch(clearJob());
      });
  };

  useEffect(() => {
    if (jobId) {
      dispatch(
        notificationsActions.setInfoNotification({
          msg: "Your file is being generated. This may take some time.",
        })
      );
      setIntervalId(setInterval(() => fetchDoc(), 5000));
    } else {
      clearInterval(intervalId);
      setJob(null);
    }
  }, [jobId]);

  useEffect(() => {
    if (job) {
      dispatch(docFetcherActions.setJobId(job));
      if (job.status === "finished" && job.doc) {
        dispatch(
          notificationsActions.setSuccessNotification({
            msg: [
              "Your file is done. If your download does not start automatically, click ",
              <a key={job.jobId} href={job.doc}>
                here
              </a>,
              ".",
            ],
          })
        );
        downloadDoc();
      }
      if (
        !!job.status &&
        ["finished", "deferred", "stopped", "canceled", "scheduled"].includes(
          job.status
        )
      ) {
        dispatch(clearJob());
      }
    }
  }, [job]);

  // eslint-disable-next-line react/jsx-no-useless-fragment
  return <></>;
}

export default DocFetcher;
