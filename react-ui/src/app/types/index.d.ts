import { AxiosError } from "axios";
import { Dispatch, SetStateAction } from "react";
import { Indicator, IndicatorArea, ValidationIssue } from "./api";

interface StepCallback {
  (
    proceed?: () => void,
    step?: number,
    setStep?: Dispatch<SetStateAction<number>>,
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
  detail?: string;
  details?: unknown;
  code?: number;
  service?: string;
  non_field_errors?: string[];
  errors?: ValidationIssue[];
  warnings?: ValidationIssue[];
  valid?: boolean;
  [key: string]: unknown;
}>;
