import { ChangeEvent } from "react";
import { Control } from "react-hook-form";
import { Submodule } from "../../types/api";
import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";

export interface SubmoduleListItemProps {
  submodule: Submodule;
  submoduleIndex: number;
  control: Control<SurveyFormState>;
  submodules: number[];
  handleSubmoduleChange: (
    checked: boolean,
    submodule: Submodule,
    event: ChangeEvent<HTMLInputElement>
  ) => void;
  isSelectedByIndicator: boolean;
  selectedIndicatorSubmoduleIdMap: Record<number, string[]>;
  selectedIndicatorMatchingSubmoduleIdMap: Record<number, string[]>;
}
