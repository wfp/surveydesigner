// import 'core-js/stable';
import "regenerator-runtime/runtime";

import axios from "axios";
import _ from "lodash";
import React from "react";
import { API } from "../../utils";

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
      let ok = true;
      let data = null;
      if (res.data && res.data.length) {
        ok = false;
        data = res.data;
      }
      return {
        ok,
        data,
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
