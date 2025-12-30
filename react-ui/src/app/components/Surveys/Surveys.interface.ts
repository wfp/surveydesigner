import { FrontendContent, SavedSurvey } from "../../types/api";
import { PrevNextStepCallback } from "../../types";

export interface SurveysProps {
  next: PrevNextStepCallback;
  frontendContent: FrontendContent[] | null;
  selectedSurveyToEdit: SavedSurvey | null;
}
