import React from "react";
import { ModuleHeader, Tooltip } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleQuestion } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../../redux/store";
import { renderTooltipMarkdown } from "../../utils";
import ModulesHeaderControls from "../Modules/HeaderControls";
import ReviewHeaderControls from "../Review/HeaderControls";
import { useSurveyWizardContext } from "../../contexts/SurveyWizardContext";

function SurveyWizardHeader() {
  const { t } = useTranslation();
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const {
    step,
    steps,
    stepsCount,
    selectedModuleCounts,
    numberOfQuestionsToBeGenerated,
  } = useSurveyWizardContext();

  const stepTooltips = [
    renderTooltipMarkdown(frontendContent, "step1Tooltip"),
    null,
    renderTooltipMarkdown(frontendContent, "step3Tooltip"),
    null,
  ];
  const showModulesCount = step === 1 && !!selectedModuleCounts.submoduleCount;
  const showQuestionsCount = step === 2 && !!numberOfQuestionsToBeGenerated;

  return (
    <ModuleHeader>
      <div className="d-flex" style={{ justifyContent: "space-between" }}>
        <div className="d-flex align-items-center">
          {t("surveyWizard.stepTitle", {
            currentStep: step + 1,
            stepsCount,
            currentStepTitle: steps[step],
          })}
          {stepTooltips[step] && (
            <Tooltip
              createRefWrapper
              content={stepTooltips[step]}
              dark
              placement="top"
              trigger="hover"
            >
              <FontAwesomeIcon
                icon={faCircleQuestion}
                className="wfp--btn__icon info-icon"
                description="help"
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
        {[1, 2].includes(step) && (
          <div className="checkbox-row">
            {step === 1 && <ModulesHeaderControls />}
            {step === 2 && <ReviewHeaderControls />}
          </div>
        )}
      </div>
    </ModuleHeader>
  );
}

export default SurveyWizardHeader;
