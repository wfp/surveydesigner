import React from "react";
import { CheckboxState } from "../../../types";
import { StepTitleWithTooltip } from "./StepTitleWithTooltip";
import { StepOneControls } from "./StepOneControls";
import { StepTwoControls } from "./StepTwoControls";

type SurveyWizardHeaderProps = {
  step: number;
  stepsCount: number;
  steps: string[];
  stepTooltips: (React.ReactNode | null)[];
  showModulesCount: boolean;
  showQuestionsCount: boolean;
  selectedModuleCounts: {
    moduleCount?: number;
    submoduleCount?: number;
  };
  numberOfQuestionsToBeGenerated: number;
  selectAllModules: CheckboxState;
  setSelectAllModules: (value: CheckboxState) => void;
  collapseAllModules: CheckboxState;
  setCollapseAllModules: (value: CheckboxState) => void;
  collapseAllIndicatorAreas: CheckboxState;
  setCollapseAllIndicatorAreas: (value: CheckboxState) => void;
  selectAllReview: CheckboxState;
  setSelectAllReview: (value: CheckboxState) => void;
  collapseAllReview: CheckboxState;
  setCollapseAllReview: (value: CheckboxState) => void;
};

export function SurveyWizardHeader({
  step,
  stepsCount,
  steps,
  stepTooltips,
  showModulesCount,
  showQuestionsCount,
  selectedModuleCounts,
  numberOfQuestionsToBeGenerated,
  selectAllModules,
  setSelectAllModules,
  collapseAllModules,
  setCollapseAllModules,
  collapseAllIndicatorAreas,
  setCollapseAllIndicatorAreas,
  selectAllReview,
  setSelectAllReview,
  collapseAllReview,
  setCollapseAllReview,
}: SurveyWizardHeaderProps) {
  const currentTooltip = stepTooltips[step];

  return (
    <div
      className="d-flex"
      style={{ justifyContent: "space-between" }}
    >
      <StepTitleWithTooltip
        step={step}
        stepsCount={stepsCount}
        steps={steps}
        tooltipContent={currentTooltip}
        showModulesCount={showModulesCount}
        showQuestionsCount={showQuestionsCount}
        selectedModuleCounts={selectedModuleCounts}
        numberOfQuestionsToBeGenerated={numberOfQuestionsToBeGenerated}
      />
      {[1, 2].includes(step) && (
        <div className="checkbox-row">
          <div className="d-flex">
            {step === 1 && (
              <StepOneControls
                selectAllModules={selectAllModules}
                setSelectAllModules={setSelectAllModules}
                collapseAllModules={collapseAllModules}
                setCollapseAllModules={setCollapseAllModules}
                collapseAllIndicatorAreas={collapseAllIndicatorAreas}
                setCollapseAllIndicatorAreas={setCollapseAllIndicatorAreas}
              />
            )}
            {step === 2 && (
              <StepTwoControls
                selectAllReview={selectAllReview}
                setSelectAllReview={setSelectAllReview}
                collapseAllReview={collapseAllReview}
                setCollapseAllReview={setCollapseAllReview}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

