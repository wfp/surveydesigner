import React from "react";
import { StepNavigation, StepNavigationItem } from "@wfp/react";
import { surveyWizardUiActions } from "../../../redux/reducers/surveyWizardUiReducer";
import { useAppDispatch, useAppSelector } from "../../../redux/store";
import { useWizardSteps } from "../hooks/useWizardSteps";

export function StepNavigationWrapper({
  className,
}: {
  className?: string;
}) {
  const dispatch = useAppDispatch();
  const { step } = useAppSelector((state) => state.surveyWizardUi);
  const steps = useWizardSteps();

  return (
    <div className="step-navigation-container">
      <StepNavigation
        selectedStep={step}
        className={`custom-step-navigation ${className || ""}`}
        role="navigation"
      >
        {steps.map((label, index) => (
          <StepNavigationItem
            key={`${label}-${index}`}
            label={label}
            page={index}
            onClick={(_e) => {
              dispatch(surveyWizardUiActions.goToStepSafe(index));
              return {};
            }}
          />
        ))}
      </StepNavigation>
    </div>
  );
}

