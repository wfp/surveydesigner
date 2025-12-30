import { Dispatch, SetStateAction } from "react";
import { PrevNextStepCallback, CheckboxState } from "../../types";
import { SavedSurvey } from "../../types/api";

export interface ModulesProps {
  next: PrevNextStepCallback;
  selectAll: CheckboxState;
  setSelectAll: (selectAll: CheckboxState) => void;
  collapseAllModules: CheckboxState;
  setCollapseAllModules: (checkboxState: CheckboxState) => void;
  collapseAllIndicatorAreas: CheckboxState;
  setCollapseAllIndicatorAreas: (checkboxState: CheckboxState) => void;
  prvsStep: number;
  step: number;
  setSelectedModuleCounts: Dispatch<
    SetStateAction<{
      moduleCount?: number;
      submoduleCount?: number;
    }>
  >;
  selectedSurveyToEdit: SavedSurvey | null;
  setIsValidating: (isValidating: boolean) => void;
}
