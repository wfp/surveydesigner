import React from "react";
import { Button, InlineLoading, Tooltip } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../../../redux/store";

export function SurveyWizardPreviousButton({
  onPreviousClick,
}: {
  onPreviousClick: () => void;
}) {
  const { t } = useTranslation();
  const { step, isCreatingSurvey } = useAppSelector(
    (state) => state.surveyWizardUi,
  );
  const savedSurveysData = useAppSelector((state) => state.savedSurveys.data);

  const shouldShowButton =
    step > 0 || (isCreatingSurvey && savedSurveysData);
  const hasSavedSurveys = !!savedSurveysData?.length;

  if (isCreatingSurvey && !savedSurveysData) {
    return <InlineLoading description="Loading saved surveys..." />;
  }

  if (!shouldShowButton) {
    return null;
  }

  const isDisabled = step === 0 && !hasSavedSurveys;

  const buttonContent = (
    <Button
      kind="secondary"
      className="wfp--form-controls__prev wfp--btn wfp--btn--secondary"
      disabled={isDisabled}
      onClick={onPreviousClick}
    >
      {step > 0 ? t("actions.previous") : t("surveyWizard.savedSurveys")}
      <FontAwesomeIcon icon={faArrowLeft} className="wfp--btn__icon" />
    </Button>
  );

  if (isDisabled) {
    return (
      <Tooltip
        className="custom-tooltip"
        createRefWrapper
        content={"There are no saved surveys"}
        dark
        placement="top-end"
        trigger="hover"
      >
        {buttonContent}
      </Tooltip>
    );
  }

  return buttonContent;
}

