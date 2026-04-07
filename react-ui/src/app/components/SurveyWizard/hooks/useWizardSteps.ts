import { useTranslation } from "react-i18next";

export const WIZARD_STEPS_COUNT = 4;

export function useWizardSteps() {
  const { t } = useTranslation();
  return [
    t("surveyWizard.steps.defineSurvey"),
    t("surveyWizard.steps.selectModules"),
    t("surveyWizard.steps.selectAdditionQuestions"),
    t("surveyWizard.steps.generatePublishSurvey"),
  ];
}
