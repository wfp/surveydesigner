// import 'core-js/stable';
import "regenerator-runtime/runtime";

import axios from "axios";
import _ from "lodash";
import React from "react";
import type { ValidationIssue, ValidationResult } from "../../types/api";
import { API } from "../../utils";
import { formatValidationIssues } from "../../utils/apiError";

export async function apiValidation(
  selectedSubmodules: number[],
  selectedIndicators: number[],
  modulesOrder: number[],
  submodulesOrder: Record<number, number[]>
) {
  const submoduleIDs: number[][] = [];

  modulesOrder.forEach((mID) => {
    submoduleIDs.push(
      submodulesOrder[mID].filter((id) => selectedSubmodules.includes(id))
    );
  });
  const allSubmoduleIDs = Object.values(submodulesOrder).flat();
  const result = await API
    .get("/order-validation/", {
      params: {
        submodule_ids: submoduleIDs.join(","),
        all_submodule_ids: allSubmoduleIDs.join(","),
        indicator_ids: selectedIndicators.join(","),
      },
    })
    .then((res) => {
      const response = res.data as ValidationResult | string[];
      if (Array.isArray(response)) {
        return {
          ok: response.length === 0,
          data: response.length ? response : null,
        };
      }

      return {
        ok: response.valid,
        data: response.valid ? null : response.errors,
      };
    })
    .catch((error) => ({
      ok: false,
      data: ["Validation could not be performed."],
    }));

  return result;
}

export function getValidationSubmoduleId(
  errors: Array<string | ValidationIssue> | null,
) {
  if (!errors) return null;

  for (const error of errors) {
    if (typeof error === "string") continue;
    const submodule =
      error.submodule ??
      (error.owner?.model === "Submodule" ? error.owner : undefined);
    if (typeof submodule?.id === "number") return submodule.id;
  }

  return null;
}

export function getErrorDisplay(
  error: string | Array<string | ValidationIssue>,
) {
  if (_.isArray(error)) {
    const messages = formatValidationIssues(error);
    const shouldScroll = messages.length > 10;

    return (
      <div
        className={
          shouldScroll
            ? "modules-validation-errors modules-validation-errors--scrollable"
            : "modules-validation-errors"
        }
      >
        {messages.map((message, index) => (
          <div
            className="modules-validation-errors__item"
            key={`${index}-${message}`}
          >
            <div className="modules-validation-errors__index">{index + 1}.</div>
            <div>{message}</div>
          </div>
        ))}
      </div>
    );
  }
  return error;
}
