import React, { useEffect, useState } from "react";
import { Controller } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faCaretDown,
  faCaretRight,
} from "@fortawesome/free-solid-svg-icons";
import { Checkbox, Link, List, ListItem, Modal } from "@wfp/react";

import { useAppDispatch, useAppSelector } from "../../redux/store";

import { submodulesActions } from "../../redux/reducers/submodulesReducer";
import { getCMSUrl, openPopup } from "../../utils/url";
import { useModules } from "../../contexts/ModulesContext";
import { Module, Submodule, SubmoduleWithQuestions } from "../../types/api";
import { SubmoduleListProps } from "./SubmoduleList.interface";

/**
 * Renders the Submodules list on Step 3 of the survey builder.
 */
function SubmoduleList({
  collapseAll,
  control,
  getRootQuestionsCount,
  numberOfQuestionsToBeGenerated,
  selectAll,
  selectedOptions,
  setCollapseAll,
  setNumberOfQuestionsToBeGenerated,
  setSelectAll,
  setSubQuestions,
  submodules,
  submodulesData,
  submodulesMap,
  subQuestions,
}: SubmoduleListProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const modulesData = useModules();
  const modules = useAppSelector((state) => state.modules?.data);
  const [moduleCollapsed, setModuleCollapsed] = useState(
    modulesData.current.review_modules_collapsed,
  );
  const [submoduleCollapsed, setSubmoduleCollapsed] = useState(
    modulesData.current.review_submodules_collapsed,
  );
  const submodulesWithSuffixes = submodules.filter(
    (submodule) =>
      submodule.root_questions.filter(
        (root) =>
          root.sub_questions.filter((sub) => sub.suffix?.name !== "_oth")
            .length,
      ).length,
  );
  const [submoduleModal, setSubmoduleModal] = useState<{
    clickedGroup: Submodule;
  } | null>(null);

  const getAllItems = (): [Submodule[], Submodule[]] => {
    const groupItems = submodules?.flatMap((submodule) => {
      const submoduleFromMap = submodulesMap[submodule.id] || {};
      return submoduleFromMap ? Object.values(submoduleFromMap) : [];
    });

    const allItems = groupItems.reduce((acc, cur) => {
      const { next } = cur;
      const itemSubQuestions = next ? Object.values(next) : [];
      const allNestedItemSubQuestions = itemSubQuestions.reduce(
        (nestedAcc, nestedCur) => {
          const { next: nestedNext } = nestedCur;
          const nestedItemSubQuestions = nestedCur
            ? Object.values(nestedNext)
            : [];
          return [...nestedAcc, ...nestedItemSubQuestions];
        },
        itemSubQuestions,
      );

      return [...acc, ...allNestedItemSubQuestions];
    }, groupItems);

    return [groupItems, allItems];
  };

  const [groupItems, allItems] = getAllItems();

  const getModuleHierarchy = () => {
    const {
      current: {
        modules_order: modulesOrder,
        submodules_order: submodulesOrder,
      },
    } = modulesData;
    return [...modulesOrder]
      .map((modId) => {
        const module = modules?.find((module) => module.id === modId);
        return {
          ...(module || { id: modId, label: "", organizations: [] }),
          submodules: submodulesOrder[modId]
            .filter((subId) =>
              submodulesWithSuffixes
                .map((submodule) => submodule.id)
                .includes(subId),
            )
            .map((subId) =>
              submodules.find((submodule) => submodule?.id === subId),
            )
            .filter(
              (submodule): submodule is SubmoduleWithQuestions => !!submodule,
            ),
        };
      })
      .filter((module) => module.submodules.length);
  };

  const modulesHierarchy = getModuleHierarchy();

  const getListItem = (item: Submodule, url: string) => {
    const {
      real_item: { name },
    } = item;
    const labelText = `${item.display} (${item.sub_questions.length})`;
    const label = isRequired(item) ? (
      <>
        {labelText} <span className="required">*</span>
      </>
    ) : (
      labelText
    );

    return (
      <ListItem key={item.id} className="submodule-item">
        <Controller
          name="sub_questions"
          control={control}
          render={(props) =>
            name !== "_oth" ? (
              <div className="d-flex">
                <Checkbox
                  id={`${item.id}`}
                  labelText={label}
                  checked={selectedOptions.has(item.id)}
                  onChange={(event, checked, customId) =>
                    handleItemChange(checked, item)
                  }
                />
                {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
                <Link onClick={() => openPopup(url)}>
                  <FontAwesomeIcon
                    icon={faArrowUpRightFromSquare}
                    className="wfp--btn__icon cms-link-icon"
                  />
                </Link>
              </div>
            ) : (
              <div />
            )
          }
        />
      </ListItem>
    );
  };

  const getTitleLabel = (
    module: Pick<Module | Submodule, "id" | "label">,
    collapsed: Set<number>,
    type: "module" | "submodule",
    weight?: number,
  ) => (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div
      className="d-flex"
      onClick={() => handleCollapseClick(module.id, type)}
      style={{ cursor: "pointer" }}
    >
      <div role="button">
        {collapsed?.has(module.id) ? (
          <FontAwesomeIcon
            style={{ verticalAlign: "middle", marginRight: "0.5rem" }}
            icon={faCaretRight}
          />
        ) : (
          <FontAwesomeIcon
            style={{ verticalAlign: "middle", marginRight: "0.5rem" }}
            icon={faCaretDown}
          />
        )}
      </div>
      <div style={{ fontWeight: weight }}>{module.label}</div>
    </div>
  );

  const handleCollapseClick = (id: number, type: "module" | "submodule") => {
    const relevantCollapsed =
      type === "submodule" ? submoduleCollapsed : moduleCollapsed;
    const relevantSetCollapsed =
      type === "submodule" ? setSubmoduleCollapsed : setModuleCollapsed;

    const isNowCollapsed = relevantCollapsed && !relevantCollapsed?.has(id);
    const newCollapsed = new Set(
      isNowCollapsed
        ? [...relevantCollapsed, id]
        : [...relevantCollapsed].filter((listId) => listId !== id),
    );

    if (isNowCollapsed) {
      if (type === "module") {
        modulesData.current.review_modules_collapsed.add(id);
      } else {
        modulesData.current.review_submodules_collapsed.add(id);
      }
    } else if (type === "module") {
      modulesData.current.review_modules_collapsed.delete(id);
    } else {
      modulesData.current.review_submodules_collapsed.delete(id);
    }

    const allModulesCollapsed = modulesHierarchy.reduce((acc, cur) => {
      const modIsCollapsed =
        type === "module" && id === cur.id
          ? isNowCollapsed
          : moduleCollapsed?.has(cur.id);
      return modIsCollapsed ? acc : false;
    }, true);

    if (allModulesCollapsed && !collapseAll.isChecked) {
      setCollapseAll({ isChecked: true, run: false });
    } else if (collapseAll.isChecked) {
      setCollapseAll({ isChecked: false, run: false });
    }

    relevantSetCollapsed(newCollapsed);
  };

  const handleItemChange = (checked: boolean, item: Submodule) => {
    if (checked) {
      // Handle item being checked
      setSubQuestions([...subQuestions, ...item.sub_questions]);
      dispatch(
        submodulesActions.setSelectedSubmodulesOptions([
          ...selectedOptions,
          item.id,
        ]),
      );
      setNumberOfQuestionsToBeGenerated(
        numberOfQuestionsToBeGenerated + item.sub_questions.length,
      );
    } else if (isRequired(item)) {
      setSubmoduleModal({ clickedGroup: item });
    } else {
      uncheckItemAndChildren(item);
    }

    // Update the select all state
    if (selectAll.isChecked && !checked) {
      setSelectAll({ isChecked: false, run: false });
    } else if (!selectAll.isChecked && checked) {
      const allIds = allItems.map((submodule) => submodule.id);
      const newSelected = [...selectedOptions, item.id];
      const newSelectedSorted = newSelected.slice().sort();
      const equal =
        allIds.length === newSelectedSorted.length &&
        allIds
          .slice()
          .sort()
          .every((value, index) => value === newSelectedSorted[index]);
      if (equal) {
        setSelectAll({ isChecked: true, run: false });
      }
    }
  };

  const uncheckItemAndChildren = (item: Submodule) => {
    const itemsToUncheck = [item, ...getAllNestedChildren(item)];
    const checkedItemsToUncheck = itemsToUncheck.filter((submodule) =>
      selectedOptions.has(submodule.id),
    );
    const itemIdsToUncheck = checkedItemsToUncheck.map(
      (submodule) => submodule.id,
    );
    const subQuestionsToRemove = checkedItemsToUncheck.flatMap(
      (submodule) => submodule.sub_questions,
    );

    itemIdsToUncheck.forEach((id) => selectedOptions.delete(id));
    setNumberOfQuestionsToBeGenerated(
      numberOfQuestionsToBeGenerated - subQuestionsToRemove.length,
    );

    dispatch(
      submodulesActions.setSelectedSubmodulesOptions([...selectedOptions]),
    );
    setSubQuestions([
      ...subQuestions.filter(
        (subQuestion) => !subQuestionsToRemove.includes(subQuestion),
      ),
    ]);
  };

  const getAllNestedChildren = (item: Submodule): Submodule[] => {
    if (!item.next) return [];
    const children = Object.values(item.next);
    const nestedChildren = children.flatMap(getAllNestedChildren);
    return [...children, ...nestedChildren];
  };

  const isRequired = (item: Submodule) => {
    const children = getAllNestedChildren(item);
    const containsRequired = (items: Submodule[]) =>
      items.some((submodule) => submodule.required);
    return item.required || containsRequired(children);
  };

  const handleSelectForMultipleItems = (items: Submodule[]) => {
    setSubQuestions([
      ...subQuestions,
      ...items.flatMap((item) => item.sub_questions),
    ]);
    dispatch(
      submodulesActions.setSelectedSubmodulesOptions([
        ...selectedOptions,
        ...items.map((item) => item.id),
      ]),
    );
  };

  const getSubQuestionsCountFromSelectedOptions = (
    selectedOptions,
    submodulesMap,
  ) => {
    let count = 0;
    const visited = new Set();

    const traverseSubmodule = (submodule) => {
      if (visited.has(submodule.id)) return;
      visited.add(submodule.id);

      if (selectedOptions.has(submodule.id)) {
        count += submodule.sub_questions.length;
      }

      Object.values(submodule.next).forEach(traverseSubmodule);
    };

    Object.values(submodulesMap).forEach((submoduleMap) =>
      Object.values(submoduleMap).forEach(traverseSubmodule),
    );

    return count;
  };

  function calculateInitialNumberOfQuestions(selectAll: {
    isChecked: boolean;
    run?: boolean;
  }) {
    const { isChecked } = selectAll;

    const rootQuestionsCount = getRootQuestionsCount(submodules);
    const selectedQuestionsCount = selectedOptions.size
      ? getSubQuestionsCountFromSelectedOptions(selectedOptions, submodulesMap)
      : 0;
    const initialQuestionCount = rootQuestionsCount + selectedQuestionsCount;
    if (!isChecked) {
      setNumberOfQuestionsToBeGenerated(initialQuestionCount);
    }
  }

  useEffect(() => {
    calculateInitialNumberOfQuestions(selectAll);
  }, [submodulesMap, selectedOptions, selectAll]);

  useEffect(() => {
    const { isChecked } = selectAll;

    const allSelected = allItems.reduce(
      (acc, cur) => (selectedOptions.has(cur.id) ? acc : false),
      true,
    );
    const allItemIds = allItems.map((item) => item.id);
    const adjustedSelectedOptions =
      [...selectedOptions].filter((id) => allItemIds.includes(id)) || [];

    if (adjustedSelectedOptions.length && allSelected && !isChecked) {
      setSelectAll({ isChecked: true, run: false });
    } else if (!allSelected && isChecked) {
      setSelectAll({ isChecked: false, run: false });
    }
  }, [selectedOptions]);

  useEffect(() => {
    const { isChecked, run } = collapseAll;
    if (run) {
      const newModulesCollapsed = isChecked
        ? new Set<number>((modules ?? []).map((module) => module.id))
        : new Set<number>();
      const newSubmodulesCollapsed = isChecked
        ? new Set<number>(submodules.map((submodule) => submodule.id))
        : new Set<number>();

      setModuleCollapsed(newModulesCollapsed);
      setSubmoduleCollapsed(newSubmodulesCollapsed);
      modulesData.current.review_modules_collapsed = newModulesCollapsed;
      modulesData.current.review_submodules_collapsed = newSubmodulesCollapsed;
    }
  }, [collapseAll]);

  function getOnlyRootQuestionsCount() {
    const rootQuestions = submodules?.flatMap(
      // eslint-disable-next-line camelcase
      ({ root_questions }) => root_questions,
    );
    return rootQuestions?.length || 0;
  }

  useEffect(() => {
    const { isChecked, run } = selectAll;

    if (run) {
      const itemSubQuestions = isChecked
        ? groupItems.flatMap((question) => [
            ...question.sub_questions,
            ...Object.values(question.next).flatMap(
              (next) => next.sub_questions,
            ),
          ])
        : [];

      // Check/Uncheck all the boxes on the UI.
      dispatch(
        submodulesActions.setSelectedSubmodulesOptions(
          isChecked ? allItems?.map((q) => q.id) : [],
        ),
      );

      // Add/Remove all of the sub questions from the data.
      setSubQuestions(itemSubQuestions);

      if (isChecked) {
        setNumberOfQuestionsToBeGenerated(
          getOnlyRootQuestionsCount() + itemSubQuestions.length,
        );
      } else {
        setNumberOfQuestionsToBeGenerated(getRootQuestionsCount(submodules));
      }

      setSelectAll({ isChecked, run: false });
    }
  }, [selectAll]);

  useEffect(() => {
    const requiredItems = allItems.filter((item) => isRequired(item));
    handleSelectForMultipleItems(requiredItems);
  }, [submodulesMap]);

  const handleModalRequestClose = () => {
    setSubmoduleModal(null);
  };

  const handleModalRequestSubmit = () => {
    if (submoduleModal) {
      const item = submoduleModal.clickedGroup;
      uncheckItemAndChildren(item);
      setSubmoduleModal(null);
    }
  };

  return !submodulesWithSuffixes.length && !submodulesData.isLoading ? (
    <div>{t("submoduleList.nothingToReview")}</div>
  ) : (
    <div>
      <Modal
        open={!!submoduleModal}
        primaryButtonText="Yes"
        secondaryButtonText="No"
        onRequestSubmit={handleModalRequestSubmit}
        onRequestClose={handleModalRequestClose}
      >
        <p className="wfp--modal-content__text">
          {(submoduleModal?.clickedGroup.sub_questions.length ?? 0) > 1
            ? t("submoduleList.deleteConfirmationSingular")
            : t("submoduleList.deleteConfirmationPlural")}
        </p>
      </Modal>

      {modulesHierarchy?.map((module) => (
        <List key={module.id}>
          <ListItem
            className="module-title"
            title={getTitleLabel(module, moduleCollapsed, "module")}
          />
          {module?.submodules.map((submodule) => (
            <List
              key={submodule.id}
              style={{
                marginLeft: "1rem",
                display: moduleCollapsed?.has(module.id) ? "none" : "",
              }}
            >
              <ListItem
                className="module-title"
                title={getTitleLabel(
                  submodule,
                  submoduleCollapsed,
                  "submodule",
                  600,
                )}
              />
              {submodulesMap[submodule.id] &&
                Object.values(submodulesMap[submodule.id]).map((firstItem) => (
                  <div
                    key={`firstItemWrapper${firstItem.id}`}
                    style={{
                      marginLeft: "1rem",
                      display: submoduleCollapsed?.has(submodule.id)
                        ? "none"
                        : "",
                    }}
                  >
                    {getListItem(
                      firstItem,
                      getCMSUrl(submodule.id, firstItem.real_item),
                    )}
                    {selectedOptions.has(firstItem.id) &&
                      Object.values(firstItem.next).map((secondItem) => (
                        <div
                          key={`secondItemWrapper${secondItem.id}`}
                          style={{ marginLeft: "1rem" }}
                        >
                          {getListItem(
                            secondItem,
                            getCMSUrl(
                              submodule.id,
                              firstItem.real_item,
                              secondItem.real_item,
                            ),
                          )}
                          {selectedOptions.has(secondItem.id) &&
                            Object.values(secondItem.next).map((thirdItem) => (
                              <div
                                key={`thirdItemWrapper${thirdItem.id}`}
                                style={{ marginLeft: "1rem" }}
                              >
                                {getListItem(
                                  thirdItem,
                                  getCMSUrl(
                                    submodule.id,
                                    firstItem.real_item,
                                    secondItem.real_item,
                                    thirdItem.real_item,
                                  ),
                                )}
                              </div>
                            ))}
                        </div>
                      ))}
                  </div>
                ))}
            </List>
          ))}
        </List>
      ))}
    </div>
  );
}

export default SubmoduleList;
