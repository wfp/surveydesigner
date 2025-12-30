import { Dispatch, SetStateAction } from "react";
import { Control } from "react-hook-form";

import { SubmodulesState } from "../../redux/reducers/submodulesReducer";
import {
  Submodule,
  SubmoduleWithQuestions,
  SubQuestion,
} from "../../types/api";
import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";
import { CheckboxState } from "../../types";

export interface SubmoduleListProps {
  collapseAll: CheckboxState;
  control: Control<SurveyFormState>;
  getRootQuestionsCount: (submodules: SubmoduleWithQuestions[]) => number;
  numberOfQuestionsToBeGenerated: number;
  selectAll: {
    isChecked: boolean;
    run: boolean;
  };
  selectedOptions: Set<number>;
  setCollapseAll: (collapseAll: CheckboxState) => void;
  setNumberOfQuestionsToBeGenerated: (numberOfQuestions: number) => void;
  setSelectAll: (selectAll: CheckboxState) => void;
  setSubQuestions: Dispatch<SetStateAction<SubQuestion[]>>;
  submodules: SubmoduleWithQuestions[];
  submodulesData: SubmodulesState;
  subQuestions: SubQuestion[];
  submodulesMap: Record<number, Record<string, Submodule>>;
}
