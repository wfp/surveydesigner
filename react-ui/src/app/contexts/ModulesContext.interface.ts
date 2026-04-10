import { PropsWithChildren } from "react";

export interface ModulesData {
  collapsed: Set<number>;
  modules_order: number[];
  modules_count?: number;
  submodules_order: Record<number, number[]>;
  submodules_count?: number;
  indicator_areas_order: number[];
  indicators_order: Record<string, number[]>;
  review_modules_collapsed: Set<number>;
  review_submodules_collapsed: Set<number>;
}

export interface ModulesProviderProps extends PropsWithChildren {
  initialValue?: ModulesData;
}
