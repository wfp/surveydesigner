import React from "react";
import { Checkbox } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { surveyWizardUiActions } from "../../../redux/reducers/surveyWizardUiReducer";
import { useAppDispatch, useAppSelector } from "../../../redux/store";

export function StepTwoControls() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { selectAllReview, collapseAllReview } = useAppSelector(
    (state) => state.surveyWizardUi,
  );

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
            dispatch(
              surveyWizardUiActions.setSelectAllReview({
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
          collapseAllReview.isChecked
            ? t("surveyWizard.expandAllSubmodules")
            : t("surveyWizard.collapseAllSubmodules")
        }
        checked={collapseAllReview.isChecked}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
          dispatch(
            surveyWizardUiActions.setCollapseAllReview({
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

