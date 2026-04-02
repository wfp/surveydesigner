import React from "react";
import { Checkbox } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { surveyWizardUiActions } from "../../../redux/reducers/surveyWizardUiReducer";
import { useAppDispatch, useAppSelector } from "../../../redux/store";

export function StepOneControls() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { selectAllModules, collapseAllModules, collapseAllIndicatorAreas } =
    useAppSelector((state) => state.surveyWizardUi);

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
            dispatch(
              surveyWizardUiActions.setSelectAllModules({
                isChecked: event.target.checked,
                run: true,
              }),
            );
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
          dispatch(
            surveyWizardUiActions.setCollapseAllModules({
              isChecked: event.target.checked,
              run: true,
            }),
          );
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
          dispatch(
            surveyWizardUiActions.setCollapseAllIndicatorAreas({
              isChecked: event.target.checked,
              run: true,
            }),
          );
        }}
        wrapperClassName="allCheckboxWrapper"
      />
    </>
  );
}

