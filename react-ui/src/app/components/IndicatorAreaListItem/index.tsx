import React, { useEffect, useState } from "react";
import { Draggable, Droppable } from "react-beautiful-dnd";

import { Link, List, ListItem, Tooltip } from "@wfp/react";

import { useModules } from "../../contexts/ModulesContext";
import { getCompareFunction } from "../../utils";
import { openPopup } from "../../utils/url";
import IndicatorList from "../IndicatorList";
import { IndicatorArea } from "../../types/api";
import { IndicatorAreaListItemProps } from "./IndicatorsAreaListItem.interface";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCaretDown,
  faCaretRight,
  faCircleInfo,
  faGripVertical,
} from "@fortawesome/free-solid-svg-icons";

function IndicatorAreaListItem({
  indicatorArea,
  index,
  handleIndicatorOnChange,
  control,
  collapseAll,
  setCollapseAll,
  watchAllFields,
}: IndicatorAreaListItemProps) {
  const modulesData = useModules();
  const [expanded, setExpanded] = useState(
    !modulesData.current.collapsed.has(indicatorArea.id),
  );
  const sortedIndicators = [...indicatorArea.indicators].sort(
    getCompareFunction(modulesData.current.indicators_order[indicatorArea.id] || []),
  );
  function saveAndSetExpanded(newExpanded: boolean) {
    if (newExpanded) {
      modulesData.current.collapsed.delete(indicatorArea.id);
      if (collapseAll.isChecked) {
        setCollapseAll({ isChecked: false, run: false });
      }
    } else {
      modulesData.current.collapsed.add(indicatorArea.id);
      if (!collapseAll.isChecked) {
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

  function getIndicatorAreaLabel(indicatorArea: IndicatorArea) {
    let label = (
      <div
        className="indicator-area-label"
        style={{
          display: "flex",
          alignItems: "center",
          cursor: "pointer",
        }}
      >
        {/* Expand/collapse */}
        <div
          role="button"
          onClick={() => saveAndSetExpanded(!expanded)}
          style={{ display: "flex", alignItems: "center" }}
        >
          {expanded ? (
            <FontAwesomeIcon
              style={{ verticalAlign: "middle", marginRight: "0.5rem" }}
              icon={faCaretDown}
            />
          ) : (
            <FontAwesomeIcon
              style={{ verticalAlign: "middle", marginRight: "0.5rem" }}
              icon={faCaretRight}
            />
          )}
        </div>
        <div style={{ marginLeft: 6 }}>{indicatorArea.label}</div>
        {indicatorArea.url && (
          <Link
            className="d-flex align-items-center"
            style={{ marginLeft: "10px" }}
            href={indicatorArea.url}
            target="_blank"
          >
            <FontAwesomeIcon
              style={{ width: 15, height: 15, verticalAlign: "middle" }}
              icon={faCircleInfo}
            />
          </Link>
        )}
      </div>
    );

    if (indicatorArea.description) {
      label = (
        <Tooltip
          content={indicatorArea.description}
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

    return (
      <div
        className="indicator-area-label-row"
        style={{
          display: "flex",
          alignItems: "center",
          width: "100%",
          marginBottom: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", flexGrow: 1 }}>
          {label}
        </div>
        <div style={{ marginLeft: 10, display: "flex", alignItems: "center" }}>
          <FontAwesomeIcon
            className="draggable-icon"
            style={{ width: 14, height: 14 }}
            icon={faGripVertical}
          />
        </div>
      </div>
    );
  }

  return (
    <Draggable draggableId={indicatorArea.id.toString()} index={index}>
      {(provided, snapshot) => (
        <div
          className={snapshot.isDragging ? "greyBackground" : "whiteBackground"}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          ref={provided.innerRef}
        >
          <List key={indicatorArea.id}>
            <ListItem
              className="indicator-area-title"
              title={getIndicatorAreaLabel(indicatorArea)}
            />
            <div style={expanded ? {} : { display: "none" }}>
              <Droppable
                droppableId={`indicatorsDroppable${indicatorArea.id}`}
                type={`${indicatorArea.id}`}
              >
                {(indicatorProvided) => (
                  <div
                    ref={indicatorProvided.innerRef}
                    {...indicatorProvided.droppableProps}
                  >
                    {sortedIndicators.map((indicator, indicatorIndex) => (
                      <IndicatorList
                        key={indicator.id}
                        {...{
                          indicator,
                          indicatorIndex,
                          control,
                          handleIndicatorOnChange,
                          watchAllFields,
                        }}
                      />
                    ))}
                    {indicatorProvided.placeholder}
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

export default IndicatorAreaListItem;
