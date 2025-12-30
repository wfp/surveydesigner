import React from "react";
import { Modal } from "@wfp/react";
import { PayloadAction } from "@reduxjs/toolkit";
import { useTranslation } from "react-i18next";
import { useAppDispatch } from "../../redux/store";
import { deleteSavedSurvey } from "../../redux/actions/savedSurveysActions";
import { SavedSurvey } from "../../types/api";

export interface DeleteSavedSurveyModalOptionsInterface {
  isOpen: boolean;
  uuid: number | null;
}

interface DeleteSavedSurveyModalProps {
  deleteSavedSurveyModalOptions: DeleteSavedSurveyModalOptionsInterface;
  setDeleteSavedSurveyModalOptions: (
    value: DeleteSavedSurveyModalOptionsInterface,
  ) => void;
  isSavedSurveyActionSuccess: (
    res: PayloadAction<any>,
    actionType: string,
  ) => void;
  selectedSavedSurvey: SavedSurvey | undefined;
}

export function DeleteSavedSurveyModal({
  deleteSavedSurveyModalOptions: { isOpen, uuid },
  setDeleteSavedSurveyModalOptions,
  isSavedSurveyActionSuccess,
  selectedSavedSurvey,
}: DeleteSavedSurveyModalProps) {
  const dispatch = useAppDispatch();
  const { t } = useTranslation();

  return (
    <Modal
      open={isOpen}
      onRequestClose={() =>
        setDeleteSavedSurveyModalOptions({ uuid: null, isOpen: false })
      }
      onRequestSubmit={() => {
        dispatch(deleteSavedSurvey({ uuid })).then((res: any) => {
          setDeleteSavedSurveyModalOptions({ uuid: null, isOpen: false });
          isSavedSurveyActionSuccess(
            res,
            "saved_surveys/DELETE_SAVEDSURVEYS/fulfilled",
          );
        });
      }}
      modalHeading={t("deleteSavedSurveyModal.modalHeading")}
      primaryButtonText={t("actions.delete")}
      secondaryButtonText={t("actions.cancel")}
      danger
    >
      <div className="delete-saved-survey-text">
        <div>
          {t("deleteSavedSurveyModal.delete")}
          <span className="survey-name">{` "${selectedSavedSurvey?.name}"?`}</span>
        </div>
        <div>{t("deleteSavedSurveyModal.actionCannotBeUndone")}</div>
      </div>
    </Modal>
  );
}
