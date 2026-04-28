import React from "react";
import { Tooltip } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleQuestion } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useSurveyWizard } from "../Context/SurveyWizardContext";

type StepTitleWithTooltipProps = {
  stepsCount: number;
  steps: string[];
  tooltipContent: React.ReactNode | null;
  showModulesCount: boolean;
  showQuestionsCount: boolean;
};

export function StepTitleWithTooltip() {
  const { t } = useTranslation();
  const {
    step,
    stepsCount,
    steps,
    stepTooltips,
    selectedModuleCounts,
    numberOfQuestionsToBeGenerated,
  } = useSurveyWizard();

  const tooltipContent = stepTooltips[step];
  const showModulesCount = step === 1;
  const showQuestionsCount = step === 2;

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

