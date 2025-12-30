import { Control } from "react-hook-form";

import { SurveyFormState } from "../../redux/reducers/surveyFormReducer";
import { Indicator } from "../../types/api";

export interface IndicatorListProps {
  indicator: Indicator;
  indicatorIndex: number;
  control: Control<SurveyFormState>;
  handleIndicatorOnChange: (checked: boolean, indicator: Indicator, event: React.ChangeEvent<HTMLInputElement>) => void;
  watchAllFields: SurveyFormState;
}
