import { PrevNextStepCallback, CheckboxState } from "../../types";
import { SavedSurvey } from "../../types/api";

export interface ReviewProps {
  next: PrevNextStepCallback;
  numberOfQuestionsToBeGenerated: number;
  selectAll: CheckboxState;
  setSelectAll: (checkboxState: CheckboxState) => void;
  collapseAll: CheckboxState;
  setCollapseAll: (checkboxState: CheckboxState) => void;
  setNumberOfQuestionsToBeGenerated: (number: number) => void;
  selectedSurveyToEdit: SavedSurvey | null;
}
