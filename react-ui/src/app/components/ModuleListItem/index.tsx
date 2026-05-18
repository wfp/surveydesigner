import React, { ChangeEvent, useEffect, useRef, useState } from "react";
import { Draggable, Droppable } from "react-beautiful-dnd";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faCaretDown,
  faCaretRight,
  faGripVertical,
  faCircleInfo,
} from "@fortawesome/free-solid-svg-icons";

import { Link, List, ListItem, Tooltip } from "@wfp/react";

import { useAppSelector } from "../../redux/store";
import { useModules } from "../../contexts/ModulesContext";
import { getCompareFunction } from "../../utils";
import SubmoduleListItem from "../SubmoduleListItem";
import { getModuleCmsUrl, openPopup } from "../../utils/url";
import { Indicator, Module, Submodule } from "../../types/api";
import { ModuleListItemProps } from "./ModuleListItem.interface";

function ModuleListItem({
  module,
  index,
  handleSubmoduleChange,
  submodules,
  control,
  collapseAll,
  setCollapseAll,
  watchAllFields,
}: ModuleListItemProps) {
  const modulesData = useModules();
  const [expanded, setExpanded] = useState(
    !modulesData.current.collapsed.has(module.id),
  );
  const submodulesData = useRef(
    [...module.submodules].sort(
      getCompareFunction(modulesData.current.submodules_order[module.id]),
    ),
  );
  const indicators = useAppSelector((state) => state.indicators.data || []);
  const selectedIndicatorIDs =
    watchAllFields.indicators?.filter((indicatorId) =>
      indicators?.find((indicator) => indicator.id === indicatorId),
    ) || [];
  const selectedIndicators =
    selectedIndicatorIDs
      .map((indicatorId) =>
        indicators?.find((indicator) => indicator.id === indicatorId),
      )
      .filter((indicator): indicator is Indicator => !!indicator) || [];
  const selectedIndicatorSubmoduleIds = new Set(
    selectedIndicators?.flatMap((indicator) =>
      indicator?.submodules.map((submodule) => submodule.id),
    ) || [],
  );
  const selectedIndicatorSubmoduleIdMap = submodulesData.current
    .map((submodule) => submodule.id)
    .reduce(
      (acc, cur) => ({
        ...acc,
        [cur]: selectedIndicators
          ?.filter((ind) =>
            ind.submodules.map((submodule) => submodule.id).includes(cur),
          )
          .map((ind) => ind.label),
      }),
      {} as Record<number, string[]>,
    );

  const selectedIndicatorMatchingSubmoduleIdMap = submodulesData.current.reduce(
    (acc, submodule) => {
      acc[submodule.id] = selectedIndicators
        .filter((indicator) =>
          submodule.root_questions.every((rootQuestion) =>
            indicator.root_questions.includes(rootQuestion),
          ),
        )
        .map((indicator) => indicator.label);
      return acc;
    },
    {} as Record<number, string[]>,
  );

  const submoduleSelectedByIndicator = (submodule: Submodule) =>
    [...selectedIndicatorSubmoduleIds].includes(submodule.id);

  function saveAndSetExpanded(newExpanded: boolean) {
    if (newExpanded) {
      modulesData.current.collapsed.delete(module.id);

      if (collapseAll.isChecked) {
        setCollapseAll({ isChecked: false, run: false });
      }
    } else {
      modulesData.current.collapsed.add(module.id);

      if (
        !collapseAll.isChecked &&
        modulesData.current.modules_count === modulesData.current.collapsed.size
      ) {
        setCollapseAll({ isChecked: true, run: false });
      }
    }
    setExpanded(newExpanded);
  }

  useEffect(() => {
    if (collapseAll.run && expanded === collapseAll.isChecked) {
      saveAndSetExpanded(!collapseAll.isChecked);
    }
  }, [collapseAll]);

  function getModuleLabel(module: Module) {
    let label = (
      <div className="survey-list-row__label" style={{ cursor: "pointer" }}>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus */}
        <div
          className="survey-list-row__toggle"
          role="button"
          onClick={() => saveAndSetExpanded(!expanded)}
        >
          {expanded ? (
            <FontAwesomeIcon
              style={{ verticalAlign: "middle" }}
              icon={faCaretDown}
            />
          ) : (
            <FontAwesomeIcon
              style={{ verticalAlign: "middle" }}
              icon={faCaretRight}
            />
          )}
        </div>
        <div className="survey-list-row__label-text">{module.label}</div>
      </div>
    );

    if (module.description) {
      label = (
        <Tooltip
          content={module.description}
          dark
          modifiers={[]}
          placement="top"
          trigger="hover"
          useWrapper
        >
          {label}
        </Tooltip>
      );
    }

    const adminUrl = getModuleCmsUrl(module);

    return (
      <div className="survey-list-row survey-list-row--heading">
        <div className="survey-list-row__label">{label}</div>
        <div className="survey-list-row__actions">
          {module.url && (
            <Link
              className="survey-list-row__icon-link"
              href={module.url}
              target="_blank"
            >
              <FontAwesomeIcon
                style={{ width: 15, height: 15, verticalAlign: "middle" }}
                icon={faCircleInfo}
              />
            </Link>
          )}
          {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
          <Link
            className="survey-list-row__icon-link"
            onClick={() => openPopup(adminUrl)}
          >
            <FontAwesomeIcon
              description={adminUrl}
              icon={faArrowUpRightFromSquare}
              className="wfp--btn__icon cms-link-icon"
            />
          </Link>
          <div className="survey-list-row__drag">
            <FontAwesomeIcon
              className="draggable-icon"
              style={{ width: 14, height: 14 }}
              icon={faGripVertical}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <Draggable draggableId={module.id.toString()} index={index}>
      {(provided, snapshot) => (
        <div
          className={snapshot.isDragging ? "greyBackground" : "whiteBackground"}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          ref={provided.innerRef}
        >
          <List key={module.id}>
            <ListItem className="module-title" title={getModuleLabel(module)} />
            <div style={expanded ? {} : { display: "none" }}>
              <Droppable
                droppableId={`submodulesDroppable${module.id}`}
                type={`${module.id}`}
              >
                {(submoduleProvided) => (
                  <div
                    ref={submoduleProvided.innerRef}
                    {...submoduleProvided.droppableProps}
                  >
                    {submodulesData.current.map((submodule, submoduleIndex) => (
                      <SubmoduleListItem
                        key={submodule.id}
                        isSelectedByIndicator={submoduleSelectedByIndicator(
                          submodule,
                        )}
                        {...{
                          submodule,
                          submoduleIndex,
                          control,
                          submodules,
                          handleSubmoduleChange,
                          selectedIndicatorSubmoduleIdMap,
                          selectedIndicatorMatchingSubmoduleIdMap,
                        }}
                      />
                    ))}
                    {submoduleProvided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          </List>
        </div>
      )}
    </Draggable>
  );
}

export default ModuleListItem;
