// import 'core-js/stable';
import "regenerator-runtime/runtime";

import axios from "axios";
import _ from "lodash";
import React from "react";
import type { ValidationResult } from "../../types/api";
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
        data: response.valid ? null : formatValidationIssues(response.errors),
      };
    })
    .catch((error) => ({
      ok: false,
      data: ["Validation could not be performed."],
    }));

  return result;
}

export function getErrorDisplay(error: string | string[]) {
  if (_.isArray(error)) {
    const shouldScroll = error.length > 10;

    return (
      <div
        className={
          shouldScroll
            ? "modules-validation-errors modules-validation-errors--scrollable"
            : "modules-validation-errors"
        }
      >
        {error.map((e, index) => (
          <div className="modules-validation-errors__item" key={`${index}-${e}`}>
            <div className="modules-validation-errors__index">
              {index + 1}.
            </div>
            <div>{e}</div>
          </div>
        ))}
      </div>
    );
  }
  return error;
}
