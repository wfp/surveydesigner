import React from "react";
import { StepNavigation, StepNavigationItem } from "@wfp/react";

type StepNavigationWrapperProps = {
  steps: string[];
  currentStep: number;
  className?: string;
  onStepClick: (index: number) => void;
};

export function StepNavigationWrapper({
  steps,
  currentStep,
  className,
  onStepClick,
}: StepNavigationWrapperProps) {
  return (
    <div className="step-navigation-container">
      <StepNavigation
        selectedStep={currentStep}
        className={`custom-step-navigation ${className || ""}`}
        role="navigation"
      >
        {steps.map((label, index) => (
          <StepNavigationItem
            key={`${label}-${index}`}
            label={label}
            page={index}
            onClick={(_e) => {
              onStepClick(index);
              return {};
            }}
          />
        ))}
      </StepNavigation>
    </div>
  );
}

