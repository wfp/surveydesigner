import React, { MutableRefObject, useContext, useRef } from "react";
import { ModulesData, ModulesProviderProps } from "./ModulesContext.interface";

const ModulesContext = React.createContext<MutableRefObject<ModulesData>>(
  {} as MutableRefObject<ModulesData>
);

export function useModules() {
  return useContext(ModulesContext);
}

export function ModulesProvider({
  children,
  initialValue,
}: ModulesProviderProps) {
  const modulesData = useRef<ModulesData>({
    collapsed: new Set(),

    modules_order: [],
    modules_count: undefined,
    submodules_order: {},
    submodules_count: undefined,

    indicator_areas_order: [],
    indicators_order: {},

    review_modules_collapsed: new Set(),
    review_submodules_collapsed: new Set(),

    ...initialValue,
  });

  return (
    <ModulesContext.Provider value={modulesData}>
      {children}
    </ModulesContext.Provider>
  );
}
