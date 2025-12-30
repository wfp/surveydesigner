import { Indicator, Module, Submodule } from "../types/api";

/**
 * @param submoduleID
 * @param firstItem
 * @param secondItem
 * @param thirdItem
 * @return {string}
 */
export const getCMSUrl = (
  submoduleID: number,
  firstItem?: Submodule["real_item"],
  secondItem?: Submodule["real_item"],
  thirdItem?: Submodule["real_item"]
): string => {
  const baseUrl = "/admin/questions/basequestion/?";
  const searchParams = new URLSearchParams();

  const rpKey = "recall_period_id";

  const recallPeriodID =
    (thirdItem && thirdItem[rpKey]) ||
    (secondItem && secondItem[rpKey]) ||
    (firstItem && firstItem[rpKey]);
  const suffix1ID = firstItem && firstItem.suffix_1_id;
  const suffix2ID = secondItem && secondItem.suffix_2_id;

  if (submoduleID) {
    searchParams.set("submodule__pk", `${submoduleID}`);
  }

  if (suffix1ID) {
    searchParams.set("sub_questions__suffix__pk", `${suffix1ID}`);
  }

  if (suffix2ID) {
    searchParams.set("sub_questions__suffix_2__pk", `${suffix2ID}`);
  }

  if (recallPeriodID) {
    searchParams.set("sub_questions__recall_period__pk", `${recallPeriodID}`);
  }

  return baseUrl + searchParams.toString();
};

export const getModuleCmsUrl = (module: Pick<Module, "id">) =>
  `/admin/questions/basequestion/?module__pk=${module.id}`;

export const getSubmoduleCmsUrl = (submodule: Pick<Submodule, "id">) =>
  `/admin/questions/basequestion/?submodule__pk=${submodule.id}`;

export const getIndicatorCmsUrl = (indicator: Pick<Indicator, "id">) =>
  `/admin/questions/basequestion/?indicators__pk=${indicator.id}`;

/**
 * Opens a pop-up for a given URL.
 *
 * @param url The URL to open,
 */
export const openPopup = (url?: string) => {
  window.open(url, "popup", "width=1200,height=600");
};
