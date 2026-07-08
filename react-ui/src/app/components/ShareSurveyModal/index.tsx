import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Button, TextInput, Tag } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { notificationsActions } from "../../redux/reducers/notificationReducer";
import { useAppDispatch } from "../../redux/store";
import Notification from "../Notification";
import { SavedSurvey } from "../../types/api";
import { getSurveyTags } from "../../utils";

export interface ShareSavedSurveyModalOptionsInterface {
  isOpen: boolean;
  uuid: number | null;
}

interface ShareSurveyModalProps {
  shareSavedSurveyModalOptions: ShareSavedSurveyModalOptionsInterface;
  setShareSavedSurveyModalOptions: (
    value: ShareSavedSurveyModalOptionsInterface,
  ) => void;
  selectedSavedSurvey: SavedSurvey | undefined;
}

export function ShareSurveyModal({
  shareSavedSurveyModalOptions: { isOpen, uuid },
  setShareSavedSurveyModalOptions,
  selectedSavedSurvey,
}: ShareSurveyModalProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();

  const handleClose = () => {
    setShareSavedSurveyModalOptions({ isOpen: false, uuid: null });
  };

  const copy = () => {
    navigator.clipboard.writeText(
      `${window.location.origin}/survey/copy/${uuid}`,
    );
    dispatch(
      notificationsActions.setSuccessNotification({
        msg: t("actions.copiedToClipboard"),
      }),
    );
  };

  const renderModalLabel = () => (
    <div className="share-survey-modal-tag">
      {getSurveyTags(selectedSavedSurvey).map((tag) => (
        <Tag type="info" key={tag}>
          {tag}
        </Tag>
      ))}
    </div>
  );

  return (
    <Modal
      id={`${uuid}` || "share-survey-modal"}
      open={isOpen}
      modalHeading={selectedSavedSurvey?.name || t("sharedLinkModal.heading")}
      modalLabel={renderModalLabel()}
      primaryButtonText={t("actions.close")}
      onRequestClose={handleClose}
      onRequestSubmit={handleClose}
      type="info"
      wide
    >
      <div className="share-survey-text-input">
        <TextInput
          disabled
          data-testid="share-survey-link"
          labelText={t("sharedLinkModal.description")}
          value={`${window.location.origin}/survey/copy/${uuid}`}
        />
        <div className="share-survey-copy-button">
          <Button onClick={() => copy()}>
            <FontAwesomeIcon icon={faCopy} />
          </Button>
        </div>
      </div>
      <Notification />
    </Modal>
  );
}
