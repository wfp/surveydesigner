import React from "react";
import { Tooltip } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleQuestion } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../../../redux/store";
import { selectSurveyWizardUi } from "../../../redux/reducers/surveyWizardUiReducer";

type StepTitleWithTooltipProps = {
  tooltipContent: React.ReactNode | null;
};

export function StepTitleWithTooltip({ tooltipContent }: StepTitleWithTooltipProps) {
  const { t } = useTranslation();
  const { step, selectedModuleCounts, numberOfQuestionsToBeGenerated } =
    useAppSelector(selectSurveyWizardUi);
  const steps = [
    t("surveyWizard.steps.defineSurvey"),
    t("surveyWizard.steps.selectModules"),
    t("surveyWizard.steps.selectAdditionQuestions"),
    t("surveyWizard.steps.generatePublishSurvey"),
  ];
  const stepsCount = steps.length;
  const showModulesCount = step === 1 && !!selectedModuleCounts.submoduleCount;
  const showQuestionsCount =
    step === 2 && !!numberOfQuestionsToBeGenerated;

  return (
    <div className="d-flex align-items-center">
      {t("surveyWizard.stepTitle", {
        currentStep: step + 1,
        stepsCount,
        currentStepTitle: steps[step],
      })}
      {tooltipContent && (
        <Tooltip
          createRefWrapper
          content={tooltipContent}
          dark
          placement="top"
          trigger="hover"
        >
          <FontAwesomeIcon
            icon={faCircleQuestion}
            className="wfp--btn__icon info-icon"
            style={{ marginLeft: "0.5rem" }}
          />
        </Tooltip>
      )}
      {(showModulesCount || showQuestionsCount) && (
        <span
          style={{
            color: "red",
            marginLeft: "10px",
            fontWeight: 500,
          }}
        >
          {showModulesCount &&
            t("surveyWizard.modulesCount", {
              moduleCount: selectedModuleCounts.moduleCount,
              submoduleCount: selectedModuleCounts.submoduleCount,
            })}
          {showQuestionsCount &&
            t("surveyWizard.questionsGeneratedCount", {
              numberOfQuestionsToBeGenerated,
            })}
        </span>
      )}
    </div>
  );
}

