import { InlineLoading, Modal, Callout } from "@wfp/react";
import React, {
  ChangeEvent,
  Dispatch,
  SetStateAction,
  SyntheticEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import { useForm } from "react-hook-form";
import {
  DragDropContext,
  Droppable,
  OnDragEndResponder,
} from "react-beautiful-dnd";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { fetchModules } from "../../redux/actions/modulesActions";
import { submodulesActions } from "../../redux/reducers/submodulesReducer";
import {
  surveyFormActions,
  SurveyFormState,
} from "../../redux/reducers/surveyFormReducer";
import ModuleListItem from "../ModuleListItem";
import IndicatorAreaListItem from "../IndicatorAreaListItem";
import { useModules } from "../../contexts/ModulesContext";
import { getCompareFunction } from "../../utils";
import { apiValidation, getErrorDisplay } from "./utils";
import {
  deriveModuleOrderFromSubmodulesOrder,
  getFirstDefinedOrder,
  getPreferredEditNestedOrder,
  getPreferredEditOrder,
  mergeOrderedIds,
} from "./ordering";
import { fetchIndicatorAreas } from "../../redux/actions/indicatorAreasActions";
import { Indicator, Module, Submodule } from "../../types/api";
import { ModulesProps } from "./Modules.interface";
import { IndicatorAreaWithIndicators } from "../../types";

function Modules({
  next,
  selectAll,
  setSelectAll,
  collapseAllModules,
  setCollapseAllModules,
  collapseAllIndicatorAreas,
  setCollapseAllIndicatorAreas,
  prvsStep,
  step,
  setSelectedModuleCounts,
  selectedSurveyToEdit,
  setIsValidating,
}: ModulesProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const { data, isLoading } = useAppSelector((state) => state.modules);
  const { data: indicatorAreasData, isLoading: indicatorAreasIsLoading } =
    useAppSelector((state) => state.indicatorAreas);
  const [submoduleModal, setSubmoduleModal] = useState<{
    clickedSubmodule: Submodule;
    event?: ChangeEvent<HTMLInputElement>;
  } | null>(null);
  const [indicatorModal, setIndicatorModal] = useState<{
    clickedIndicator: Indicator;
    event?: ChangeEvent<HTMLInputElement>;
  } | null>(null);
  const [submitError, setSubmitError] = useState<string | string[] | null>(
    null,
  );
  const { control, handleSubmit, setValue, getValues, watch, register } =
    useForm<SurveyFormState>({
      defaultValues: {
        ...surveyForm,
        sub_questions: [],
      },
    });
  const modulesData = useModules();
  const [sortedModules, setSortedModules] = useState<Module[]>([]);
  const [sortedIndicatorAreas, setSortedIndicatorAreas] = useState<
    IndicatorAreaWithIndicators[]
  >([]);
  const watchAllFields = watch();
  const values = {
    submodules: watchAllFields.submodules || [],
    indicators: watchAllFields.indicators || [],
  };
  // The module request depends on the definition selected in step 1. The
  // wizard can mount this step in the same render that commits that
  // definition to Redux, so keep a scalar key and refetch if the committed
  // criteria arrive just after mount.
  const moduleCriteriaKey = [
    surveyForm.category?.id ?? "",
    surveyForm.type?.id ?? "",
    surveyForm.mode?.id ?? "",
    surveyForm.attributes.join(","),
    surveyForm.organizations.map(({ id }) => id).join(","),
  ].join("|");
  const isEditingSavedSurvey = !!selectedSurveyToEdit;
  const hasSavedOrSessionState =
    isEditingSavedSurvey ||
    surveyForm.modules_order.length > 0 ||
    surveyForm.submodules_order.length > 0 ||
    surveyForm.indicator_areas_order.length > 0 ||
    Object.keys(surveyForm.indicators_order || {}).length > 0;

  function isVisibleSubmodule(submodule: Submodule) {
    return submodule.is_active || surveyForm.submodules.includes(submodule.id);
  }
  function handleIndicatorOnChange(
    checked: boolean,
    clickedIndicator: Indicator,
    event?: ChangeEvent<HTMLInputElement>,
  ) {
    const inds = getValues("indicators") || [];
    const { id } = clickedIndicator;
    const isMandatory = clickedIndicator.is_mandatory;
    if (checked) {
      setValue("indicators", [...inds, id]);
    } else {
      if (isMandatory) {
        setIndicatorModal({ clickedIndicator, event });
      }
      setValue(
        "indicators",
        inds.filter((ind) => ind !== id),
      );
    }
  }

  function debounce<F extends (...args: any[]) => any>(
    func: F,
    delay: number,
  ): (...funcArgs: Parameters<F>) => void {
    let debounceTimer: ReturnType<typeof setTimeout>;
    return (...args: Parameters<F>) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => func(...args), delay);
    };
  }

  const debouncedValidation = useCallback(
    debounce((proceed, step, setGoToStep) => {
      handleSubmit((data) => {
        if (!data.submodules) {
          data.submodules = [];
        } else if (!data.submodules.length) {
          setSubmitError(t("modules.errors.selectOneSubModule"));
          setGoToStep?.(step ?? 0);
          setIsValidating(false);
          return;
        }

        const {
          // eslint-disable-next-line camelcase
          current: { modules_order, submodules_order },
        } = modulesData;

        apiValidation(
          getValues("submodules"),
          getValues("indicators") ?? [],
          modules_order,
          submodules_order,
        ).then((result) => {
          if (result.ok) {
            const orderedData = {
              ...data,
              modules_order: [...modules_order],
              // eslint-disable-next-line camelcase
              submodules: modules_order
                // eslint-disable-next-line camelcase
                .flatMap((modId) => submodules_order[modId])
                .filter((subId) => data.submodules.includes(subId)),
              indicator_areas_order: [
                ...modulesData.current.indicator_areas_order,
              ],
              indicators_order: { ...modulesData.current.indicators_order },
              submodules_order: modules_order.flatMap(
                (modId) => submodules_order[modId],
              ),
            };
            dispatch(surveyFormActions.setSurveyData(orderedData));
            proceed?.();
          } else {
            setSubmitError(result.data);
            setGoToStep?.(step ?? 0);
          }
          setIsValidating(false);
        });
      })();
    }, 100),
    [handleSubmit, setIsValidating],
  );

  function handleSubmoduleChange(
    checked: boolean,
    clickedSubmodule: Submodule,
    event?: ChangeEvent<HTMLInputElement>,
  ) {
    const submodules = getValues("submodules");
    const { id } = clickedSubmodule;
    const isMandatory = clickedSubmodule.is_mandatory;
    if (checked) {
      const newSubmodules = [...submodules, id];
      setValue("submodules", newSubmodules);
      setModuleCountsFromSubmodules(newSubmodules);

      if (
        !selectAll.isChecked &&
        newSubmodules.length === modulesData.current.submodules_count
      ) {
        setSelectAll({ isChecked: true, run: false });
      }
    } else {
      if (isMandatory) {
        setSubmoduleModal({ clickedSubmodule, event });
      }
      const newSubmodules = submodules.filter((submodule) => submodule !== id);
      setValue("submodules", newSubmodules);
      setModuleCountsFromSubmodules(newSubmodules);

      if (selectAll.isChecked) {
        setSelectAll({ isChecked: false, run: false });
      }
    }
  }

  function selectAllFunc(checked: boolean) {
    const ids =
      checked && data
        ? data
            .flatMap((module) =>
              module.submodules.filter((submodule) =>
                isVisibleSubmodule(submodule),
              ),
            )
            .map((submodule) => submodule.id)
        : [];
    setValue("submodules", ids);

    setSelectedModuleCounts({
      moduleCount: checked ? modulesData.current.modules_count : 0,
      submoduleCount: checked ? modulesData.current.submodules_count : 0,
    });
  }

  function setNewModuleOrder(newOrder: number[]) {
    modulesData.current.modules_order = newOrder;
    const newModulesOrder = [...sortedModules];
    newModulesOrder.sort(getCompareFunction(modulesData.current.modules_order));
    setSortedModules(newModulesOrder);
  }

  function setNewIndicatorAreaOrder(newOrder: number[]) {
    modulesData.current.indicator_areas_order = newOrder;
    const newIndicatorAreasOrder = [...sortedIndicatorAreas];
    newIndicatorAreasOrder.sort(
      getCompareFunction(modulesData.current.indicator_areas_order),
    );
    setSortedIndicatorAreas(newIndicatorAreasOrder);
  }

  const handleDragEnd: OnDragEndResponder = (result) => {
    const { destination, source, draggableId, type } = result;
    if (!destination) {
      return;
    }

    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    if (type === "MODULES") {
      const newModuleOrder = [...modulesData.current.modules_order];
      newModuleOrder.splice(source.index, 1);
      newModuleOrder.splice(destination.index, 0, parseInt(draggableId, 10));
      setNewModuleOrder(newModuleOrder);
      return;
    }
    if (type === "INDICATOR-AREAS") {
      const newIndicatorAreaOrder = [
        ...modulesData.current.indicator_areas_order,
      ];
      newIndicatorAreaOrder.splice(source.index, 1);
      newIndicatorAreaOrder.splice(
        destination.index,
        0,
        parseInt(draggableId, 10),
      );
      setNewIndicatorAreaOrder(newIndicatorAreaOrder);
      return;
    }

    if (destination.droppableId !== source.droppableId) {
      return;
    }
    const moduleID = parseInt(type, 10);
    if (draggableId.includes("indicator")) {
      const newIndicatorOrder = [
        ...modulesData.current.indicators_order[moduleID],
      ];
      const indicatorID = newIndicatorOrder.splice(source.index, 1)[0];
      newIndicatorOrder.splice(destination.index, 0, indicatorID);

      const newOrder = {
        ...modulesData.current.indicators_order,
      };

      newOrder[moduleID] = newIndicatorOrder;
      modulesData.current.indicators_order = newOrder;
      setSortedIndicatorAreas([...sortedIndicatorAreas]);
    } else {
      const newSubmodulesOrder = [
        ...modulesData.current.submodules_order[moduleID],
      ];
      const submoduleID = newSubmodulesOrder.splice(source.index, 1)[0];
      newSubmodulesOrder.splice(destination.index, 0, submoduleID);

      const newOrder = {
        ...modulesData.current.submodules_order,
      };

      newOrder[moduleID] = newSubmodulesOrder;
      modulesData.current.submodules_order = newOrder;
      setSortedModules([...sortedModules]);
    }
  };

  function getModulesFromSubmodules(submodules: number[]) {
    return Object.entries(modulesData.current.submodules_order)
      .filter((entry) =>
        entry[1].reduce((acc, cur) => acc || submodules.includes(cur), false),
      )
      .map((entry) => +entry[0]);
  }

  function setModuleCountsFromSubmodules(submodules: number[]) {
    const visibleSubmodules = submodules.filter((id) =>
      data?.some((module) =>
        module.submodules.some(
          (sub) => sub.id === id && isVisibleSubmodule(sub),
        ),
      ),
    );

    const visibleModules =
      data?.filter((module) =>
        module.submodules.some(
          (sub) =>
            isVisibleSubmodule(sub) && visibleSubmodules.includes(sub.id),
        ),
      ) ?? [];

    setSelectedModuleCounts({
      moduleCount: visibleModules.length,
      submoduleCount: visibleSubmodules.length,
    });
  }

  useEffect(() => {
    register("submodules");
    register("indicators");
    setSelectAll({ isChecked: false, run: true });
    dispatch(fetchIndicatorAreas());
  }, [dispatch, register, setSelectAll]);

  useEffect(() => {
    dispatch(submodulesActions.clearSubmodules());
    dispatch(fetchModules());
  }, [dispatch, moduleCriteriaKey]);

  useEffect(() => {
    next((proceed, step, setGoToStep) => {
      debouncedValidation(proceed, step, setGoToStep);
    });
  }, [next, debouncedValidation]);

  useEffect(() => {
    if (data) {
      const savedSubmodulesOrder = getPreferredEditOrder({
        surveyFormOrder: surveyForm.submodules_order,
        selectedSurveyOrder: selectedSurveyToEdit?.submodules_order,
        isEditing: isEditingSavedSurvey,
      });
      const submodulesIDs: number[] = [];
      const visibleModules = data
        .map((module) => ({
          ...module,
          submodules: module.submodules.filter((submodule) =>
            isVisibleSubmodule(submodule),
          ),
        }))
        .filter((module) => module.submodules.length > 0);
      const visibleModuleIds = visibleModules.map((module) => module.id);
      const derivedModulesOrder = deriveModuleOrderFromSubmodulesOrder(
        savedSubmodulesOrder,
        visibleModules,
      );

      modulesData.current.modules_order = mergeOrderedIds(
        getPreferredEditOrder({
          currentOrder: modulesData.current.modules_order,
          surveyFormOrder: surveyForm.modules_order,
          selectedSurveyOrder: selectedSurveyToEdit?.modules_order,
          fallbackOrder: derivedModulesOrder,
          isEditing: isEditingSavedSurvey,
        }),
        visibleModuleIds,
      );

      Object.keys(modulesData.current.submodules_order).forEach((moduleId) => {
        if (!visibleModuleIds.includes(Number(moduleId))) {
          delete modulesData.current.submodules_order[moduleId];
        }
      });

      const tempSortedModules = [...visibleModules].sort(
        getCompareFunction(modulesData.current.modules_order),
      );

      tempSortedModules.forEach((module) => {
        const visibleSubmoduleIds = module.submodules.map(
          (submodule) => submodule.id,
        );
        const savedOrderForModule = savedSubmodulesOrder.filter((submoduleId) =>
          visibleSubmoduleIds.includes(submoduleId),
        );

        modulesData.current.submodules_order[module.id] = mergeOrderedIds(
          getFirstDefinedOrder(
            modulesData.current.submodules_order[module.id],
            savedOrderForModule,
          ),
          visibleSubmoduleIds,
        );

        module.submodules.forEach((submodule) => {
          if (
            surveyForm.submodules.includes(submodule.id) ||
            (prvsStep <= step && submodule.is_mandatory)
          ) {
            submodulesIDs.push(submodule.id);
          }
        });
      });

      modulesData.current.modules_count = tempSortedModules.length;
      modulesData.current.submodules_count = tempSortedModules.reduce(
        (count, module) => count + module.submodules.length,
        0,
      );

      const tempSortedModulesWithSortedSubmodules = tempSortedModules.map(
        (module) => ({
          ...module,
          submodules: [...module.submodules].sort(
            getCompareFunction(modulesData.current.submodules_order[module.id]),
          ),
        }),
      );

      setSortedModules(tempSortedModulesWithSortedSubmodules);

      const submodulesToUse = hasSavedOrSessionState
        ? surveyForm.submodules
        : submodulesIDs;

      setValue("submodules", submodulesToUse);
      setModuleCountsFromSubmodules(submodulesToUse); // setSelectedModuleCounts on loading data
    }
  }, [data]);

  useEffect(() => {
    if (indicatorAreasData) {
      const savedIndicatorAreaOrder = getPreferredEditOrder({
        surveyFormOrder: surveyForm.indicator_areas_order,
        selectedSurveyOrder: selectedSurveyToEdit?.indicator_areas_order,
        isEditing: isEditingSavedSurvey,
      });
      const indicatorsIDs: number[] = [];
      const indicatorAreaIds = indicatorAreasData.map(
        (indicatorArea) => indicatorArea.id,
      );

      modulesData.current.indicator_areas_order = mergeOrderedIds(
        getFirstDefinedOrder(
          modulesData.current.indicator_areas_order,
          savedIndicatorAreaOrder,
        ),
        indicatorAreaIds,
      );

      Object.keys(modulesData.current.indicators_order).forEach(
        (indicatorAreaId) => {
          if (!indicatorAreaIds.includes(Number(indicatorAreaId))) {
            delete modulesData.current.indicators_order[indicatorAreaId];
          }
        },
      );

      const tempSortedIndicatorAreas = [...indicatorAreasData].sort(
        getCompareFunction(modulesData.current.indicator_areas_order),
      );

      tempSortedIndicatorAreas.forEach((indicatorArea) => {
        const tempIndicatorIDs: number[] = [];

        indicatorArea.indicators.forEach((indicator) => {
          tempIndicatorIDs.push(indicator.id);
          if (
            surveyForm.indicators?.includes(indicator.id) ||
            (prvsStep <= step && indicator.is_mandatory)
          ) {
            indicatorsIDs.push(indicator.id);
          }
        });

        modulesData.current.indicators_order[indicatorArea.id] =
          mergeOrderedIds(
            getPreferredEditNestedOrder({
              key: indicatorArea.id,
              currentOrderMap: modulesData.current.indicators_order,
              surveyFormOrderMap: surveyForm.indicators_order,
              selectedSurveyOrderMap: selectedSurveyToEdit?.indicators_order,
              isEditing: isEditingSavedSurvey,
            }),
            tempIndicatorIDs,
          );
      });
      const indicatorsToUse = hasSavedOrSessionState
        ? surveyForm.indicators || []
        : indicatorsIDs;
      setValue("indicators", indicatorsToUse);
      setSortedIndicatorAreas([...tempSortedIndicatorAreas]);
    }
  }, [indicatorAreasData]);

  useEffect(() => {
    const { isChecked, run } = selectAll;
    if (run) {
      selectAllFunc(isChecked);
      setSelectAll({ isChecked, run: false });
    }
  }, [selectAll]);

  return (
    <form>
      <Modal
        open={!!indicatorModal}
        primaryButtonText="Yes"
        secondaryButtonText="No"
        onRequestSubmit={() => {
          if (indicatorModal?.event) {
            indicatorModal.event.target.checked = false;
            handleIndicatorOnChange(
              false,
              indicatorModal.clickedIndicator,
              indicatorModal.event,
            );
          }
          setIndicatorModal(null);
        }}
        onRequestClose={() => {
          if (!indicatorModal) return;
          if (indicatorModal.event) {
            indicatorModal.event.target.checked = true;
          }
          handleIndicatorOnChange(
            true,
            indicatorModal.clickedIndicator,
            indicatorModal.event,
          );
          setIndicatorModal(null);
        }}
      >
        <p className="wfp--modal-content__text">
          {t("modules.errors.mandatoryIndicator")}
        </p>
      </Modal>

      <Modal
        open={!!submoduleModal}
        primaryButtonText="Yes"
        secondaryButtonText="No"
        onRequestSubmit={() => {
          setSubmoduleModal(null);
        }}
        onRequestClose={() => {
          if (!submoduleModal) return;
          if (submoduleModal.event) {
            submoduleModal.event.target.checked = true;
          }
          handleSubmoduleChange(true, submoduleModal.clickedSubmodule);
          setSubmoduleModal(null);
        }}
      >
        <p className="wfp--modal-content__text">
          {t("modules.errors.mandatoryModule")}
        </p>
      </Modal>

      <div
        style={{
          position: "fixed",
          bottom: 20,
          right: 20,
          zIndex: 2,
          width: "min(42rem, calc(100vw - 2rem))",
        }}
      >
        {submitError && (
          <Callout
            className="modules-validation-callout"
            iconDescription="close"
            kind="error"
            lowContrast
            statusIconDescription=""
            subtitle={getErrorDisplay(submitError)}
            title="Error"
            onClick={() => setSubmitError(null)}
            // eslint-disable-next-line jsx-a11y/aria-role
            role="error_notification"
            isDismissible={true}
          />
        )}
      </div>

      {isLoading && <InlineLoading description="loading..." />}
      {data &&
        !isLoading &&
        (!data.length ? (
          <div>{t("modules.errors.noModules")}</div>
        ) : (
          <div className="d-flex">
            <div className="flex-column">
              <h6 style={{ marginBottom: "10px" }}>{t("modules.title")}</h6>
              <DragDropContext onDragEnd={handleDragEnd}>
                <Droppable droppableId="modulesDroppable" type="MODULES">
                  {(provided) => (
                    <div ref={provided.innerRef} {...provided.droppableProps}>
                      {sortedModules.map((module, index) => {
                        return (
                          <ModuleListItem
                            key={module.id}
                            module={module}
                            index={index}
                            handleSubmoduleChange={handleSubmoduleChange}
                            submodules={values.submodules}
                            control={control}
                            collapseAll={collapseAllModules}
                            setCollapseAll={setCollapseAllModules}
                            watchAllFields={watchAllFields}
                          />
                        );
                      })}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </DragDropContext>
            </div>
            <div className="flex-column">
              {!!indicatorAreasData?.length && !indicatorAreasIsLoading && (
                <>
                  <h6 style={{ marginBottom: "10px" }}>
                    {t("modules.indicatorAreas.title")}
                  </h6>
                  <DragDropContext onDragEnd={handleDragEnd}>
                    <Droppable
                      droppableId="modulesDroppable"
                      type="INDICATOR-AREAS"
                    >
                      {(provided) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.droppableProps}
                        >
                          {sortedIndicatorAreas.map((indicatorArea, index) => (
                            <IndicatorAreaListItem
                              key={indicatorArea.id}
                              indicatorArea={indicatorArea}
                              index={index}
                              handleIndicatorOnChange={handleIndicatorOnChange}
                              control={control}
                              collapseAll={collapseAllIndicatorAreas}
                              setCollapseAll={setCollapseAllIndicatorAreas}
                              watchAllFields={watchAllFields}
                            />
                          ))}
                          {provided.placeholder}
                        </div>
                      )}
                    </Droppable>
                  </DragDropContext>
                </>
              )}
            </div>
          </div>
        ))}
    </form>
  );
}

export default Modules;
