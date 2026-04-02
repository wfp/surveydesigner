import React from "react";
import { Button, ModuleFooter } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faFloppyDisk } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { SavedSurvey } from "../../../types/api";
import { SurveyWizardPreviousButton } from "./SurveyWizardPreviousButton";

type SurveyWizardFooterProps = {
  step: number;
  stepsCount: number;
  isCreatingSurvey: boolean;
  isValidating: boolean;
  savedSurveysData: SavedSurvey[] | null | undefined;
  onPreviousClick: () => void;
  onNextClick: () => void;
  onCreateSurveyClick: () => void;
  onSaveClick: () => void;
};

export function SurveyWizardFooter({
  step,
  stepsCount,
  isCreatingSurvey,
  isValidating,
  savedSurveysData,
  onPreviousClick,
  onNextClick,
  onCreateSurveyClick,
  onSaveClick,
}: SurveyWizardFooterProps) {
  const { t } = useTranslation();

  return (
    <ModuleFooter>
      <div className="wfp--form-controls">
        <div>
          <SurveyWizardPreviousButton
            step={step}
            isCreatingSurvey={isCreatingSurvey}
            savedSurveysData={savedSurveysData}
            onPreviousClick={onPreviousClick}
          />
        </div>
        <div>
          {isCreatingSurvey && step < stepsCount - 1 ? (
            <Button
              kind="secondary"
              className="wfp--form-controls__next wfp--btn wfp--btn--secondary"
              disabled={step === 1 && isValidating}
              onClick={onNextClick}
            >
              {t("actions.next")}
              <FontAwesomeIcon icon={faArrowRight} className="wfp--btn__icon" />
            </Button>
          ) : (
            step === 0 && (
              <Button kind="secondary" onClick={onCreateSurveyClick}>
                {t("surveyWizard.createSurvey")}
              </Button>
            )
          )}
        </div>
        {step === stepsCount - 1 && (
          <div>
            <Button
              kind="secondary"
              className="wfp--form-controls__next"
              onClick={onSaveClick}
            >
              {t("actions.save")}
              <FontAwesomeIcon icon={faFloppyDisk} className="wfp--btn__icon" />
            </Button>
          </div>
        )}
      </div>
    </ModuleFooter>
  );
}

