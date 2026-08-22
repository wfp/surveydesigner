import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Cookies } from "react-cookie";
import { FaFileExcel, FaFileWord } from "react-icons/fa";
import Select from "react-select";
import { iconWfpHumEvaluationPos } from "@wfp/icons";
import { Button, Text, InlineLoading, Loading } from "@wfp/react";
import {
  generateDoc,
  getDataForGeneration,
  getXLS,
} from "../../utils/generate";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { useModules } from "../../contexts/ModulesContext";
import { fetchProjects } from "../../redux/actions/projectsActions";
import { API, capitalize } from "../../utils";
import { renderApiErrorMessage } from "../../utils/apiError";
import { clearJob } from "../../redux/actions/docFetcherActions";
import { notificationsActions } from "../../redux/reducers/notificationReducer";
import {
  UserProjectListAPIResponse,
  UploadResponse,
  UserAPIKey,
} from "../../types/api";
import { GenerateProps } from "./Generate.interface";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileAlt, faSearch } from "@fortawesome/free-solid-svg-icons";

function Generate({ next }: GenerateProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const auth = useAppSelector((state) => state.auth);
  const [user, setUser] = useState(auth.user);
  const { jobId, status, position } = useAppSelector(
    (state) => state.docFetcher,
  );
  const canPushToOtherSite = user && user.sites && !!user.sites.length;
  const projects = useAppSelector((state) => state.projects);
  const [selectedProject, setSelectedProject] =
    useState<UserProjectListAPIResponse | null>(null);
  const [selectedSite, setSelectedSite] = useState<UserAPIKey | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(
    null,
  );
  const [uploading, setUploading] = useState(false);
  const [xlsLoading, setXlsLoading] = useState(false);
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const modulesData = useModules();

  const withoutProjects =
    projects && projects.data && projects.data.length === 0;
  const allowSending = selectedProject || withoutProjects || uploading;

  useEffect(() => {
    if (canPushToOtherSite && selectedSite) {
      dispatch(fetchProjects(selectedSite.id));
    }
    setSelectedProject(null);
  }, [selectedSite]);

  useEffect(() => {
    next();
  }, [next]);

  useEffect(() => {
    API.get("/accounts/user/").then((res) => {
      setUser(res.data);
    });
  }, []);

  function uploadXLS() {
    setUploading(true);
    const data = {
      site: selectedSite?.name,
      id: selectedSite?.id,
      project_id: selectedProject && selectedProject.id,
      ...getDataForGeneration(surveyForm, modulesData),
    };

    if (selectedSite?.skip_projects) {
      data.id = selectedSite?.id; // for KOBO - project is an API key
      data.project_id = null;
    }

    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    API.post<UploadResponse>("/upload/", data, {
      headers: {
        "X-CSRFToken": csrfToken,
      },
    })
      .then((res) => {
        setUploading(false);
        setUploadResponse(res.data);
      })
      .catch((err) => {
        setUploading(false);
        dispatch(
          notificationsActions.setErrorNotification({
            msg: renderApiErrorMessage(
              err,
              "The survey could not be published.",
            ),
            title: t("generate.notification.uploadError"),
          }),
        );
      });
  }
  useEffect(() => {
    if (projects && projects.error) {
      const err = projects.error;
      dispatch(
        notificationsActions.setErrorNotification({
          msg: renderApiErrorMessage(
            err,
            "Projects could not be loaded for this publishing site.",
          ),
          title: t("generate.notification.getProjectError"),
        }),
      );
    }
  }, [projects, projects.error]);

  useEffect(() => {
    if (uploading) {
      dispatch(
        notificationsActions.setInfoNotification({
          msg: t("generate.notification.uploadLocation", {
            name: selectedSite?.name,
          }),
        }),
      );
    }
    if (uploadResponse) {
      dispatch(
        notificationsActions.setSuccessNotification({
          msg: t("generate.notification.uploadConfirmation", {
            name: selectedSite?.name,
          }),
        }),
      );
    }
  }, [uploadResponse, uploading]);

  return (
    <form className="w-100 h-100 d-flex align-items-center">
      <div className="d-flex w-100">
        <div className="flex-column d-flex" style={{ flexDirection: "column" }}>
          {canPushToOtherSite && !uploadResponse && (
            <Text kind="h6">{t("generate.title")}</Text>
          )}
          <div
            className="flex-column d-flex justify-content-center align-items-center"
            style={{ flexDirection: "column" }}
          >
            <div
              style={{
                marginBottom: "1rem",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Button
                kind="primary"
                className="wfp--form-controls__next wfp--btn wfp--btn--primary"
                onClick={() => {
                  setXlsLoading(true);
                  getXLS(dispatch, surveyForm, modulesData).finally(() =>
                    setXlsLoading(false),
                  );
                }}
                style={{
                  marginBottom: "1rem",
                  backgroundColor: xlsLoading ? undefined : "#008767",
                  width: "230px",
                }}
                disabled={xlsLoading}
              >
                {xlsLoading ? (
                  <InlineLoading description={t("generate.downloadingXls")} />
                ) : (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "row",
                      alignItems: "center",
                      textAlign: "right",
                    }}
                  >
                    <div>
                      <FaFileExcel
                        style={{
                          fontSize: "x-large",
                          marginTop: "5px",
                          marginLeft: "-5px",
                        }}
                      />
                    </div>
                    <div style={{ marginLeft: "5px" }}>
                      {t("generate.download.xls")}
                    </div>
                  </div>
                )}
              </Button>
              <Button
                kind="primary"
                className="wfp--form-controls__next wfp--btn wfp--btn--primary"
                onClick={() => generateDoc(dispatch, surveyForm, modulesData)}
                style={{ width: "230px" }}
                disabled={!!jobId}
              >
                {jobId ? (
                  <InlineLoading
                    description={
                      status
                        ? `${capitalize(status)} ${t("generate.generatingDoc")}`
                        : t("generate.generatingDoc")
                    }
                  />
                ) : (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "row",
                      alignItems: "center",
                      textAlign: "right",
                    }}
                  >
                    <div>
                      <FaFileWord
                        style={{
                          fontSize: "x-large",
                          marginTop: "5px",
                          marginLeft: "-5px",
                        }}
                      />
                    </div>
                    <div style={{ marginLeft: "5px" }}>
                      {t("generate.download.word")}
                    </div>
                  </div>
                )}
              </Button>
              {jobId && (
                // eslint-disable-next-line jsx-a11y/anchor-is-valid, jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
                <a
                  onClick={() => dispatch(clearJob({ isCancelled: true }))}
                  style={{ cursor: "pointer", direction: "rtl" }}
                >
                  {t("actions.cancel")}
                </a>
              )}
            </div>
          </div>
        </div>

        {uploadResponse && (
          <>
            <div style={{ width: "1px", borderLeft: "1px solid #d8e0e5" }} />
            <div
              className="flex-column d-flex justify-content-center"
              style={{ flexDirection: "column" }}
            >
              <div className="d-flex" style={{ justifyContent: "center" }}>
                <Button
                  kind="primary"
                  className="wfp--form-controls__next wfp--btn wfp--btn--primary"
                  target="_blank"
                  href={uploadResponse.preview_url}
                  icon={
                    <span
                      style={{ position: "relative", display: "inline-block" }}
                    >
                      <FontAwesomeIcon icon={faFileAlt} size="2x" />
                      <FontAwesomeIcon
                        icon={faSearch}
                        size="1x"
                        style={{
                          position: "absolute",
                          right: 0,
                          bottom: 0,
                          color: "#0a6eb4", // match your theme
                          background: "white",
                          borderRadius: "50%",
                        }}
                      />
                    </span>
                  }
                  iconReverse
                >
                  {t("generate.preview")}
                </Button>
              </div>
            </div>
          </>
        )}

        {canPushToOtherSite && !uploadResponse && (
          <>
            <div style={{ width: "1px", borderLeft: "1px solid #d8e0e5" }} />
            <div
              className="flex-column d-flex justify-content-center"
              style={{ flexDirection: "column" }}
            >
              <div style={{ textTransform: "uppercase" }}>
                <Text kind="h6">{t("generate.publish")}</Text>
              </div>

              <div
                className="wfp--form-item"
                style={{ marginTop: "2rem", marginBottom: "2rem" }}
              >
                {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                <label htmlFor="id_site_select" className="wfp--label">
                  {t("generate.site")}
                </label>
                <Select
                  className="wfp--react-select-container"
                  classNamePrefix="wfp--react-select"
                  id="id_site_select"
                  isClearable
                  defaultValue={null}
                  value={selectedSite}
                  getOptionLabel={(opt) => `${opt.name}`}
                  getOptionValue={(opt) => `${opt.name}`}
                  options={user.sites}
                  onChange={(e) => {
                    setSelectedSite(e);
                  }}
                />
              </div>
              {projects.isLoading && (
                <div
                  id="projects_loading"
                  style={{
                    display: "flex",
                    flexDirection: "row",
                    alignItems: "center",
                    alignSelf: "center",
                  }}
                >
                  <Loading withOverlay={false} small />
                </div>
              )}
              {selectedSite &&
                projects &&
                projects.data &&
                !projects.isLoading && (
                  <>
                    {!selectedSite.skip_projects && (
                      <div
                        className="wfp--form-item"
                        style={{ marginBottom: "2rem" }}
                      >
                        {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                        <label
                          htmlFor="id_project_select"
                          className="wfp--label"
                        >
                          {t("generate.projects")}
                        </label>
                        <Select
                          className="wfp--react-select-container"
                          classNamePrefix="wfp--react-select"
                          id="id_project_select"
                          isClearable
                          isDisabled={!selectedSite}
                          defaultValue={null}
                          value={selectedProject}
                          getOptionLabel={(opt) => opt.name}
                          getOptionValue={(opt) => `${opt.id}`}
                          options={projects.data}
                          onChange={(e) => {
                            setSelectedProject(e);
                          }}
                        />
                      </div>
                    )}

                    {!uploading && (
                      <div
                        className="d-flex"
                        style={{ justifyContent: "flex-end" }}
                      >
                        <Button
                          kind="primary"
                          disabled={!allowSending}
                          className="wfp--form-controls__next wfp--btn wfp--btn--primary"
                          // eslint-disable-next-line react/jsx-no-bind
                          onClick={uploadXLS}
                        >
                          {t("generate.publish")}
                        </Button>
                      </div>
                    )}

                    {uploading && <InlineLoading description="uploading..." />}
                  </>
                )}
            </div>
          </>
        )}
      </div>
    </form>
  );
}

export default Generate;
