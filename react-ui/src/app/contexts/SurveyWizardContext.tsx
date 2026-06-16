import React, {
  Dispatch,
  ReactNode,
  SetStateAction,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { CheckboxState } from "../types";
import { SavedSurvey } from "../types/api";

interface ModuleCounts {
  moduleCount?: number;
  submoduleCount?: number;
}

interface SurveyWizardContextValue {
  steps: string[];
  paths: string[];
  stepsCount: number;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  prvsStep: number;
  setPrvsStep: Dispatch<SetStateAction<number>>;
  goToStep: number;
  setGoToStep: Dispatch<SetStateAction<number>>;
  nextClickCount: number;
  setNextClickCount: Dispatch<SetStateAction<number>>;
  isValidating: boolean;
  setIsValidating: Dispatch<SetStateAction<boolean>>;
  selectedSurveyToEdit: SavedSurvey | null;
  setSelectedSurveyToEdit: Dispatch<SetStateAction<SavedSurvey | null>>;
  isCreatingSurvey: boolean;
  setIsCreatingSurvey: Dispatch<SetStateAction<boolean>>;
  selectAllModules: CheckboxState;
  setSelectAllModules: Dispatch<SetStateAction<CheckboxState>>;
  selectAllReview: CheckboxState;
  setSelectAllReview: Dispatch<SetStateAction<CheckboxState>>;
  collapseAllModules: CheckboxState;
  setCollapseAllModules: Dispatch<SetStateAction<CheckboxState>>;
  collapseAllIndicatorAreas: CheckboxState;
  setCollapseAllIndicatorAreas: Dispatch<SetStateAction<CheckboxState>>;
  collapseAllReview: CheckboxState;
  setCollapseAllReview: Dispatch<SetStateAction<CheckboxState>>;
  selectedModuleCounts: ModuleCounts;
  setSelectedModuleCounts: Dispatch<SetStateAction<ModuleCounts>>;
  numberOfQuestionsToBeGenerated: number;
  setNumberOfQuestionsToBeGenerated: Dispatch<SetStateAction<number>>;
  modulesContextKey: number;
  refreshModulesContext: () => void;
}

interface SurveyWizardProviderProps {
  children: ReactNode;
  steps: string[];
  paths: string[];
  initialIsCreatingSurvey: boolean;
}

const defaultCheckboxState: CheckboxState = {
  isChecked: false,
  run: false,
};

const SurveyWizardContext = createContext<SurveyWizardContextValue | undefined>(
  undefined,
);

export function SurveyWizardProvider({
  children,
  steps,
  paths,
  initialIsCreatingSurvey,
}: SurveyWizardProviderProps) {
  const [step, setStep] = useState(0);
  const [prvsStep, setPrvsStep] = useState(0);
  const [goToStep, setGoToStep] = useState(0);
  const [nextClickCount, setNextClickCount] = useState(0);
  const [isValidating, setIsValidating] = useState(false);
  const [selectedSurveyToEdit, setSelectedSurveyToEdit] =
    useState<SavedSurvey | null>(null);
  const [isCreatingSurvey, setIsCreatingSurvey] = useState(
    initialIsCreatingSurvey,
  );
  const [selectAllModules, setSelectAllModules] =
    useState<CheckboxState>(defaultCheckboxState);
  const [selectAllReview, setSelectAllReview] =
    useState<CheckboxState>(defaultCheckboxState);
  const [collapseAllModules, setCollapseAllModules] =
    useState<CheckboxState>(defaultCheckboxState);
  const [collapseAllIndicatorAreas, setCollapseAllIndicatorAreas] =
    useState<CheckboxState>(defaultCheckboxState);
  const [collapseAllReview, setCollapseAllReview] =
    useState<CheckboxState>(defaultCheckboxState);
  const [selectedModuleCounts, setSelectedModuleCounts] =
    useState<ModuleCounts>({
      moduleCount: 0,
      submoduleCount: 0,
    });
  const [numberOfQuestionsToBeGenerated, setNumberOfQuestionsToBeGenerated] =
    useState(0);
  const [modulesContextKey, setModulesContextKey] = useState(0);

  const refreshModulesContext = useCallback(() => {
    setModulesContextKey((value) => value + 1);
  }, []);

  const value = useMemo(
    () => ({
      steps,
      paths,
      stepsCount: steps.length,
      step,
      setStep,
      prvsStep,
      setPrvsStep,
      goToStep,
      setGoToStep,
      nextClickCount,
      setNextClickCount,
      isValidating,
      setIsValidating,
      selectedSurveyToEdit,
      setSelectedSurveyToEdit,
      isCreatingSurvey,
      setIsCreatingSurvey,
      selectAllModules,
      setSelectAllModules,
      selectAllReview,
      setSelectAllReview,
      collapseAllModules,
      setCollapseAllModules,
      collapseAllIndicatorAreas,
      setCollapseAllIndicatorAreas,
      collapseAllReview,
      setCollapseAllReview,
      selectedModuleCounts,
      setSelectedModuleCounts,
      numberOfQuestionsToBeGenerated,
      setNumberOfQuestionsToBeGenerated,
      modulesContextKey,
      refreshModulesContext,
    }),
    [
      steps,
      paths,
      step,
      prvsStep,
      goToStep,
      nextClickCount,
      isValidating,
      selectedSurveyToEdit,
      isCreatingSurvey,
      selectAllModules,
      selectAllReview,
      collapseAllModules,
      collapseAllIndicatorAreas,
      collapseAllReview,
      selectedModuleCounts,
      numberOfQuestionsToBeGenerated,
      modulesContextKey,
      refreshModulesContext,
    ],
  );

  return (
    <SurveyWizardContext.Provider value={value}>
      {children}
    </SurveyWizardContext.Provider>
  );
}

export function useSurveyWizardContext() {
  const context = useContext(SurveyWizardContext);
  if (!context) {
    throw new Error(
      "useSurveyWizardContext must be used within SurveyWizardProvider",
    );
  }
  return context;
}
