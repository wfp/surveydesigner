import React from "react";
import { StepNavigation, StepNavigationItem } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { surveyWizardUiActions } from "../../../redux/reducers/surveyWizardUiReducer";
import { useAppDispatch, useAppSelector } from "../../../redux/store";

export function StepNavigationWrapper({
  className,
}: {
  className?: string;
}) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { step } = useAppSelector((state) => state.surveyWizardUi);
  const steps = [
    t("surveyWizard.steps.defineSurvey"),
    t("surveyWizard.steps.selectModules"),
    t("surveyWizard.steps.selectAdditionQuestions"),
    t("surveyWizard.steps.generatePublishSurvey"),
  ];

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

