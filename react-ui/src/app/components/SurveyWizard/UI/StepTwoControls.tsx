import React from "react";
import { Checkbox } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { useSurveyWizard } from "../Context/SurveyWizardContext";

export function StepTwoControls() {
  const { t } = useTranslation();
  const {
    selectAllReview,
    setSelectAllReview,
    collapseAllReview,
    setCollapseAllReview,
  } = useSurveyWizard();

  return (
    <>
      <div style={{ marginRight: "3px" }}>
        <Checkbox
          id="id-submodule-select-all"
          labelText={
            selectAllReview.isChecked
              ? t("surveyWizard.deselectAllSubmodules")
              : t("surveyWizard.selectAllSubmodules")
          }
          checked={selectAllReview.isChecked}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
            setSelectAllReview({
              isChecked: event.target.checked,
              run: true,
            });
          }}
          wrapperClassName="allCheckboxWrapper"
        />
      </div>
      <Checkbox
        id="id-module-collapse-all"
        labelText={
          collapseAllReview.isChecked
            ? t("surveyWizard.expandAllSubmodules")
            : t("surveyWizard.collapseAllSubmodules")
        }
        checked={collapseAllReview.isChecked}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
          setCollapseAllReview({
            isChecked: event.target.checked,
            run: true,
          });
        }}
        wrapperClassName="allCheckboxWrapper"
      />
    </>
  );
}

