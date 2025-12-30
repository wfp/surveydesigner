import React, { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FaFileExcel, FaFileWord, FaCopy } from "react-icons/fa";
import { Loading, Tag, InlineLoading } from "@wfp/react";
import { Button } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { IconType } from "react-icons";
import { unwrapResult } from "@reduxjs/toolkit";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import {
  fetchSavedSurvey,
  fetchSavedSurveys,
  getSavedSurveyCopy,
} from "../../redux/actions/savedSurveysActions";
import { getSurveyTags, capitalize } from "../../utils";
import Divider from "../Divider";
import { savedSurveysActions } from "../../redux/reducers/savedSurveysReducer";
import { generateDoc, getXLS } from "../../utils/generate";
import { clearJob } from "../../redux/actions/docFetcherActions";
import DocFetcher from "../DocFetcher";

interface ActionButtonInterface {
  label: string | JSX.Element;
  onClick: () => void;
  icon: IconType;
  backgroundColor?: string;
  disabled?: boolean;
}

function SharedLinkLandingPage() {
  const { t } = useTranslation();
  const { detail: sharedSurvey, isLoading } = useAppSelector(
    (state) => state.savedSurveys,
  );
  const { jobId, status, position } = useAppSelector(
    (state) => state.docFetcher,
  );
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { uuid } = useParams<{ uuid: string }>();

  useEffect(() => {
    dispatch(fetchSavedSurvey({ uuid }));
  }, [uuid]);

  if (isLoading) {
    return <Loading withOverlay={false} />;
  }

  if (!sharedSurvey) {
    return (
      <div className="saved-survey-not-found">
        {t("sharedLinkLandingPage.surveyNotFound")}
        <Button>
          <Link to="/">{t("actions.goToHome")}</Link>
        </Button>
      </div>
    );
  }

  const actionButtons: ActionButtonInterface[] = [
    {
      label: `${t("sharedLinkLandingPage.createCopy")}`,
      onClick: async () => {
        const res = await dispatch(
          getSavedSurveyCopy({ uuid: sharedSurvey.uuid }),
        ).unwrap();
        const newUuid = res.uuid ?? res.data?.uuid; // safe either way
        if (!newUuid) throw new Error("No uuid in copy response");
        dispatch(savedSurveysActions.clearSavedSurveyDetail());
        dispatch(fetchSavedSurveys({}));
        navigate("/design/survey", { state: { surveyId: newUuid, copiedSurvey: res.data } });
      },
      kind: "primary",
      icon: FaCopy,
    },
    {
      label: t("generate.download.xls"),
      onClick: () => getXLS(dispatch, sharedSurvey, undefined, true),
      kind: "primary",
      icon: FaFileExcel,
      backgroundColor: "#008767",
    },
    {
      label: jobId ? (
        <InlineLoading
          description={
            status
              ? `${capitalize(status)} ${t(
                  "sharedLinkLandingPage.generatingDocument",
                )}...`
              : `${t("sharedLinkLandingPage.generatingDocument")}...`
          }
        />
      ) : (
        `${t("generate.download.word")}`
      ),
      onClick: () => {
        generateDoc(dispatch, sharedSurvey, undefined, true);
      },
      kind: "primary",
      icon: FaFileWord,
      disabled: !!jobId,
    },
  ];

  return (
    <div>
      <DocFetcher />
      <div className="shared-survey-title-container">
        <h1 className="wfp--modal-header__heading">{sharedSurvey?.name}</h1>
        <div className="share-survey-modal-tag">
          {getSurveyTags(sharedSurvey).map((tag) => (
            <Tag key={tag} type="info">
              {tag}
            </Tag>
          ))}
        </div>
      </div>
      <Divider />
      <div className="shared-survey-content">
        <div className="shared-survey-actions">
          {actionButtons.map(({ icon: Icon, ...actionButton }) => (
            <Button
              key={
                typeof actionButton.label === "string"
                  ? actionButton.label
                  : "word"
              }
              kind="primary"
              className="wfp--form-controls__next wfp--btn wfp--btn--primary"
              onClick={actionButton.onClick}
              style={{
                marginBottom: "1rem",
                backgroundColor: actionButton.backgroundColor,
                width: "230px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  textAlign: "right",
                }}
              >
                <Icon
                  style={{
                    fontSize: "x-large",
                    marginTop: "5px",
                    marginLeft: "-5px",
                  }}
                />
                <div style={{ marginLeft: "5px" }}>{actionButton.label}</div>
              </div>
            </Button>
          ))}
        </div>
      </div>
      <Divider />
      <div className="shared-survey-footer">
        <Button href="/" kind="secondary">
          <FontAwesomeIcon
            icon={faArrowLeft}
            className="wfp--btn__icon nav-icon"
          />
          {t("actions.goToHome")}
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
  );
}

export default SharedLinkLandingPage;
