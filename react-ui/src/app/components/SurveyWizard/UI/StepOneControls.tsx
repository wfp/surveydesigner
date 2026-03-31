import React from "react";
import { Checkbox } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { CheckboxState } from "../../../types";

type StepOneControlsProps = {
  selectAllModules: CheckboxState;
  setSelectAllModules: (value: CheckboxState) => void;
  collapseAllModules: CheckboxState;
  setCollapseAllModules: (value: CheckboxState) => void;
  collapseAllIndicatorAreas: CheckboxState;
  setCollapseAllIndicatorAreas: (value: CheckboxState) => void;
};

export function StepOneControls({
  selectAllModules,
  setSelectAllModules,
  collapseAllModules,
  setCollapseAllModules,
  collapseAllIndicatorAreas,
  setCollapseAllIndicatorAreas,
}: StepOneControlsProps) {
  const { t } = useTranslation();

  return (
    <>
      <div style={{ marginRight: "3px" }}>
        <Checkbox
          id="id-submodule-select-all"
          labelText={
            selectAllModules.isChecked
              ? t("surveyWizard.deselectAllSubmodules")
              : t("surveyWizard.selectAllSubmodules")
          }
          checked={selectAllModules.isChecked}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
            setSelectAllModules({
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
          collapseAllModules.isChecked
            ? t("surveyWizard.expandAllSubmodules")
            : t("surveyWizard.collapseAllSubmodules")
        }
        checked={collapseAllModules.isChecked}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
          setCollapseAllModules({
            isChecked: event.target.checked,
            run: true,
          });
        }}
        wrapperClassName="allCheckboxWrapper"
      />
      <Checkbox
        id="id-indicator-area-collapse-all"
        labelText={
          collapseAllIndicatorAreas.isChecked
            ? t("surveyWizard.expandAllIndicators")
            : t("surveyWizard.collapseAllIndicators")
        }
        checked={collapseAllIndicatorAreas.isChecked}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
          setCollapseAllIndicatorAreas({
            isChecked: event.target.checked,
            run: true,
          });
        }}
        wrapperClassName="allCheckboxWrapper"
      />
    </>
  );
}

