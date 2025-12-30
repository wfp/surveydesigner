import { Control } from "react-hook-form";

import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";
import { CheckboxState, IndicatorAreaWithIndicators } from "../../types";
import {Indicator} from "../../types/api";

export interface IndicatorAreaListItemProps {
  indicatorArea: IndicatorAreaWithIndicators;
  index: number;
  handleIndicatorOnChange: (checked: boolean, indicator: Indicator) => void;
  control: Control<SurveyFormState>;
  collapseAll: CheckboxState;
  setCollapseAll: (collapseAll: CheckboxState) => void;
  watchAllFields: SurveyFormState;
}
