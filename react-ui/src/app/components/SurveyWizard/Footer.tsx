import React from "react";
import { Button, InlineLoading, ModuleFooter, Tooltip } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faArrowRight,
  faFloppyDisk,
} from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { surveyFormActions } from "../../redux/reducers/surveyFormReducer";
import { useSurveyWizardContext } from "../../contexts/SurveyWizardContext";

interface SurveyWizardFooterProps {
  clearSavedSurveyFilters: () => void;
  resetSurveyData: () => void;
  saveSurvey: () => void;
}

function SurveyWizardFooter({
  clearSavedSurveyFilters,
  resetSurveyData,
  saveSurvey,
}: SurveyWizardFooterProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const savedSurveys = useAppSelector((state) => state.savedSurveys);
  const {
    step,
    stepsCount,
    isCreatingSurvey,
    setIsCreatingSurvey,
    setSelectedSurveyToEdit,
    isValidating,
    setIsValidating,
    setGoToStep,
    nextClickCount,
    setNextClickCount,
    refreshModulesContext,
  } = useSurveyWizardContext();

  const renderPreviousButton = () => {
    const shouldShowButton =
      step > 0 || (isCreatingSurvey && savedSurveys.data);
    const hasSavedSurveys = savedSurveys.data && savedSurveys.data.length > 0;

    if (isCreatingSurvey && !savedSurveys.data) {
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
        onClick={() => {
          if (step > 0) {
            setGoToStep(step - 1);
          } else {
            setIsCreatingSurvey(false);
            resetSurveyData();
          }
        }}
      >
        {step > 0 ? t("actions.previous") : t("surveyWizard.savedSurveys")}
        <FontAwesomeIcon
          icon={faArrowLeft}
          className="wfp--btn__icon"
          description="previous"
        />
      </Button>
    );
    if (isDisabled) {
      return (
        <Tooltip
          className="custom-tooltip"
          createRefWrapper
          content="There are no saved surveys"
          dark
          placement="top-end"
          trigger="hover"
        >
          {buttonContent}
        </Tooltip>
      );
    }

    return buttonContent;
  };

  return (
    <ModuleFooter>
      <div className="wfp--form-controls">
        <div>{renderPreviousButton()}</div>
        <div>
          {isCreatingSurvey && step < stepsCount - 1 ? (
            <Button
              kind="secondary"
              className="wfp--form-controls__next wfp--btn wfp--btn--secondary"
              disabled={step === 1 && isValidating}
              onClick={() => {
                if (step === 1) {
                  setIsValidating(true);
                }
                setGoToStep(step + 1);
                setNextClickCount(nextClickCount + 1);
              }}
            >
              {t("actions.next")}
              <FontAwesomeIcon
                icon={faArrowRight}
                className="wfp--btn__icon"
                description="next"
              />
            </Button>
          ) : (
            step === 0 && (
              <Button
                kind="secondary"
                onClick={() => {
                  setIsCreatingSurvey(true);
                  setSelectedSurveyToEdit(null);
                  dispatch(surveyFormActions.resetSurveyData({}));
                  refreshModulesContext();
                  clearSavedSurveyFilters();
                }}
              >
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
              onClick={saveSurvey}
            >
              {t("actions.save")}
              <FontAwesomeIcon
                icon={faFloppyDisk}
                className="wfp--btn__icon"
                description="save"
              />
            </Button>
          </div>
        )}
      </div>
    </ModuleFooter>
  );
}

export default SurveyWizardFooter;
