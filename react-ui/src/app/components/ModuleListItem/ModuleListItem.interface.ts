import { ChangeEvent } from "react";
import { Control } from "react-hook-form";

import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";
import { Module, Submodule } from "../../types/api";
import { CheckboxState } from "../../types";

export interface ModuleListItemProps {
  module: Module;
  index: number;
  handleSubmoduleChange: (
    checked: boolean,
    submodule: Submodule,
    event: ChangeEvent<HTMLInputElement>
  ) => void;
  submodules: number[];
  control: Control<SurveyFormState>;
  collapseAll: CheckboxState;
  setCollapseAll: (collapseAll: CheckboxState) => void;
  watchAllFields: SurveyFormState;
}
