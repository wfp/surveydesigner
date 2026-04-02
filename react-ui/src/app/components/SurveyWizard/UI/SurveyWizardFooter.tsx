import React from "react";
import { Button, ModuleFooter } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faFloppyDisk } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { surveyWizardUiActions } from "../../../redux/reducers/surveyWizardUiReducer";
import { useAppDispatch, useAppSelector } from "../../../redux/store";
import { SurveyWizardPreviousButton } from "./SurveyWizardPreviousButton";

export function SurveyWizardFooter({
  onPreviousClick,
  onCreateSurveyClick,
  onSaveClick,
}: {
  onPreviousClick: () => void;
  onCreateSurveyClick: () => void;
  onSaveClick: () => void;
}) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { step, isCreatingSurvey, isValidating } = useAppSelector(
    (state) => state.surveyWizardUi,
  );
  const stepsCount = 4;

  return (
    <ModuleFooter>
      <div className="wfp--form-controls">
        <div>
          <SurveyWizardPreviousButton onPreviousClick={onPreviousClick} />
        </div>
        <div>
          {isCreatingSurvey && step < stepsCount - 1 ? (
            <Button
              kind="secondary"
              className="wfp--form-controls__next wfp--btn wfp--btn--secondary"
              disabled={step === 1 && isValidating}
              onClick={() => {
                if (step === 1) {
                  dispatch(surveyWizardUiActions.setIsValidating(true));
                }
                dispatch(surveyWizardUiActions.setGoToStep(step + 1));
              }}
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

