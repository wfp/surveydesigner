import React, { useEffect, useRef, useState } from "react";
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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const currentJobIdRef = useRef<number | null>(null);
  const downloadedJobIdRef = useRef<number | null>(null);
  const { jobId } = useAppSelector((state) => state.docFetcher);

  const dispatch = useAppDispatch();

  const fetchDoc = (activeJobId: number) => {
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    API.get("/generate-doc/", {
      headers: {
        "X-CSRFToken": csrfToken,
      },
      params: {
        jobId: activeJobId,
      },
    })
      .then((res) => {
        if (currentJobIdRef.current !== activeJobId) return;
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
            msg: `${err.response.data.message
                ? err.response.data.message
                : err.message
              }`,
          })
        );
        dispatch(clearJob());
      });
  };

  const downloadDoc = (docUrl: string) => {
    const timestamp = new Date().getTime().toString();
    if (!docUrl) return;

    API.get(docUrl, {
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
      currentJobIdRef.current = jobId;
      downloadedJobIdRef.current = null;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      dispatch(
        notificationsActions.setInfoNotification({
          msg: "Your file is being generated. This may take some time.",
        })
      );
      intervalRef.current = setInterval(() => fetchDoc(jobId), 5000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setJob(null);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId, dispatch]);

  useEffect(() => {
    if (job) {
      if (currentJobIdRef.current !== job.jobId) return;
      dispatch(docFetcherActions.setJobId(job));
      if (
        job.status === "finished" &&
        job.doc &&
        downloadedJobIdRef.current !== job.jobId
      ) {
        downloadedJobIdRef.current = job.jobId;
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
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
        downloadDoc(job.doc);
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
