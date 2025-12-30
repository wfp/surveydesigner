import { AxiosError } from "axios";
import { Dispatch, SetStateAction } from "react";
import { Indicator, IndicatorArea } from "./api";

interface StepCallback {
  (
    proceed?: () => void,
    step?: number,
    setStep?: Dispatch<SetStateAction<number>>
  ): void;
}

export interface PrevNextStepCallback {
  (previous?: StepCallback, next?: StepCallback): void;
}

export interface CheckboxState {
  isChecked: boolean;
  run: boolean;
}

export interface IndicatorAreaWithIndicators extends IndicatorArea {
  indicators: Indicator[];
}

export type ApiError = AxiosError<{
  message?: string;
  non_field_errors?: string[];
}>;
