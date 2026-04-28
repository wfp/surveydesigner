import React from "react";
import { StepTitleWithTooltip } from "./StepTitleWithTooltip";
import { StepOneControls } from "./StepOneControls";
import { StepTwoControls } from "./StepTwoControls";
import { useSurveyWizard } from "../Context/SurveyWizardContext";

type SurveyWizardHeaderProps = {
  stepsCount: number;
  steps: string[];
  stepTooltips: (React.ReactNode | null)[];
  showModulesCount: boolean;
  showQuestionsCount: boolean;
};

export function SurveyWizardHeader() {
  const { step, stepsCount, steps, stepTooltips } = useSurveyWizard();
  const currentTooltip = stepTooltips[step];

  const showModulesCount = step === 1;
  const showQuestionsCount = step === 2;

  return (
    <div
      className="d-flex"
      style={{ justifyContent: "space-between" }}
    >
      <StepTitleWithTooltip />
      {[1, 2].includes(step) && (
        <div className="checkbox-row">
          <div className="d-flex">
            {step === 1 && <StepOneControls />}
            {step === 2 && <StepTwoControls />}
          </div>
        </div>
      )}
    </div>
  );
}

