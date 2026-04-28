import React from "react";
import { Button, ModuleFooter } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faFloppyDisk } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { SavedSurvey } from "../../../types/api";
import { SurveyWizardPreviousButton } from "./SurveyWizardPreviousButton";
import { useSurveyWizard } from "../Context/SurveyWizardContext";

export function SurveyWizardFooter() {
  const { t } = useTranslation();
  const {
    step,
    stepsCount,
    isCreatingSurvey,
    isValidating,
    saveSurvey,
    goToStep,
    setGoToStep,
    setIsCreatingSurvey,
    resetSurveyData,
    savedSurveys,
  } = useSurveyWizard();

  const onPreviousClick = () => {
    if (step > 0) {
      setGoToStep(step - 1);
    } else {
      setIsCreatingSurvey(false);
      resetSurveyData();
    }
  };

  const onNextClick = () => {
    if (step === 1) {
      // Validation logic is handled within Modules component using the next hook
    }
    setGoToStep(step + 1);
  };

  const onCreateSurveyClick = () => {
    setIsCreatingSurvey(true);
  };

  return (
    <ModuleFooter>
      <div className="wfp--form-controls">
        <div>
          <SurveyWizardPreviousButton
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
              onClick={() => {
                void saveSurvey();
              }}
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

