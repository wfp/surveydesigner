import React from "react";
import { StepTitleWithTooltip } from "./StepTitleWithTooltip";
import { StepOneControls } from "./StepOneControls";
import { StepTwoControls } from "./StepTwoControls";
import { useAppSelector } from "../../../redux/store";
import { renderTooltipMarkdown } from "../../../utils";

export function SurveyWizardHeader() {
  const { step } = useAppSelector((state) => state.surveyWizardUi);
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const step3Tooltip = renderTooltipMarkdown(frontendContent, "step3Tooltip");
  const step1Tooltip = renderTooltipMarkdown(frontendContent, "step1Tooltip");
  const currentTooltip = [step1Tooltip, null, step3Tooltip, null][step];

  return (
    <div
      className="d-flex"
      style={{ justifyContent: "space-between" }}
    >
      <StepTitleWithTooltip tooltipContent={currentTooltip} />
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

