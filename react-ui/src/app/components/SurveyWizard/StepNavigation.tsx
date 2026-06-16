import React, { useCallback } from "react";
import { StepNavigation, StepNavigationItem } from "@wfp/react";
import { useSurveyWizardContext } from "../../contexts/SurveyWizardContext";

function SurveyWizardStepNavigation() {
  const { steps, step, setGoToStep, setIsValidating } =
    useSurveyWizardContext();

  const handleStepClick = useCallback(
    (targetIndex: number) => {
      if (targetIndex === step) return;
      if (targetIndex > step && step === 1) {
        setIsValidating(true);
      } else {
        setIsValidating(false);
      }

      setGoToStep(targetIndex);
    },
    [setGoToStep, setIsValidating, step],
  );

  return (
    <div className="step-navigation-container">
      <StepNavigation
        selectedStep={step}
        className="custom-step-navigation"
        role="navigation"
      >
        {steps.map((label, index) => (
          <StepNavigationItem
            key={`${label}-${index}`}
            label={label}
            page={index}
            onClick={() => {
              handleStepClick(index);
              return {};
            }}
          />
        ))}
      </StepNavigation>
    </div>
  );
}

export default SurveyWizardStepNavigation;
