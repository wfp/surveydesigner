type WithId = {
  id: number;
};

type ModuleWithSubmodules = WithId & {
  submodules: WithId[];
};

type OrderMap = Record<string | number, number[]>;

export function getFirstDefinedOrder(
  ...orders: Array<number[] | undefined>
): number[] {
  return orders.find((order) => !!order?.length) || [];
}

export function getFirstDefinedNestedOrder(
  key: number,
  ...orderMaps: Array<OrderMap | undefined>
): number[] {
  for (const orderMap of orderMaps) {
    const order = orderMap?.[key] || orderMap?.[String(key)];
    if (order?.length) {
      return order;
    }
  }
  return [];
}

export function getPreferredEditOrder({
  currentOrder,
  surveyFormOrder,
  selectedSurveyOrder,
  fallbackOrder,
  isEditing,
}: {
  currentOrder?: number[];
  surveyFormOrder?: number[];
  selectedSurveyOrder?: number[];
  fallbackOrder?: number[];
  isEditing: boolean;
}): number[] {
  return getFirstDefinedOrder(
    currentOrder,
    ...(isEditing
      ? [selectedSurveyOrder, surveyFormOrder]
      : [surveyFormOrder, selectedSurveyOrder]),
    fallbackOrder,
  );
}

export function getPreferredEditNestedOrder({
  key,
  currentOrderMap,
  surveyFormOrderMap,
  selectedSurveyOrderMap,
  isEditing,
}: {
  key: number;
  currentOrderMap?: OrderMap;
  surveyFormOrderMap?: OrderMap;
  selectedSurveyOrderMap?: OrderMap;
  isEditing: boolean;
}): number[] {
  return getFirstDefinedNestedOrder(
    key,
    currentOrderMap,
    ...(isEditing
      ? [selectedSurveyOrderMap, surveyFormOrderMap]
      : [surveyFormOrderMap, selectedSurveyOrderMap]),
  );
}

export function mergeOrderedIds(
  preferredOrder: number[] | undefined,
  availableIds: number[],
): number[] {
  const available = new Set(availableIds);
  const seen = new Set<number>();
  const ordered = (preferredOrder || []).filter((id) => {
    if (!available.has(id) || seen.has(id)) {
      return false;
    }
    seen.add(id);
    return true;
  });

  const missing = availableIds.filter((id) => !seen.has(id));
  return [...ordered, ...missing];
}

export function deriveModuleOrderFromSubmodulesOrder(
  submodulesOrder: number[] | undefined,
  modules: ModuleWithSubmodules[],
): number[] {
  const moduleBySubmoduleId = new Map<number, number>();
  modules.forEach((module) => {
    module.submodules.forEach((submodule) => {
      moduleBySubmoduleId.set(submodule.id, module.id);
    });
  });

  const seen = new Set<number>();
  const orderedModuleIds: number[] = [];

  (submodulesOrder || []).forEach((submoduleId) => {
    const moduleId = moduleBySubmoduleId.get(submoduleId);
    if (moduleId && !seen.has(moduleId)) {
      seen.add(moduleId);
      orderedModuleIds.push(moduleId);
    }
  });

  return orderedModuleIds;
}
