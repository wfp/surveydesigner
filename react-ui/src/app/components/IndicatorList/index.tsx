import React from "react";
import { Draggable } from "react-beautiful-dnd";
import { Control, Controller } from "react-hook-form";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faCircleInfo,
  faGripVertical,
} from "@fortawesome/free-solid-svg-icons";

import { Checkbox, Link, ListItem, Tooltip } from "@wfp/react";

import { getIndicatorCmsUrl, openPopup } from "../../utils/url";
import { useAppSelector } from "../../redux/store";
import { Indicator } from "../../types/api";
import { IndicatorListProps } from "./IndicatorsList.interface";

function IndicatorList({
  indicator,
  indicatorIndex,
  control,
  handleIndicatorOnChange,
  watchAllFields,
}: IndicatorListProps) {
  const { data: indicators } = useAppSelector((state) => state.indicators);
  function getIndicatorLabel(indicator: Indicator) {
    let label = indicator.is_mandatory ? (
      <>
        {indicator.label} <span className="required">*</span>
      </>
    ) : (
      indicator.label
    );

    label = <div style={{ minWidth: "fit-content" }}>{label}</div>;
    if (!indicator.description) {
      return label;
    }

    return (
      <Tooltip
        content={indicator.description}
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
  const adminUrl = getIndicatorCmsUrl(indicator);

  return (
    <Draggable
      draggableId={`indicator-${indicator.id.toString()}`}
      index={indicatorIndex}
    >
      {(indicatorProvidedNext, indicatorSnapshot) => (
        <div
          className={
            indicatorSnapshot.isDragging ? "greyBackground" : "whiteBackground"
          }
          {...indicatorProvidedNext.draggableProps}
          {...indicatorProvidedNext.dragHandleProps}
          ref={indicatorProvidedNext.innerRef}
        >
          <ListItem key={indicator.id} className="submodule-item">
            <Controller
              name="indicators"
              control={control}
              render={({ field: { onChange, value } }) => (
                <div className="d-flex">
                  <Checkbox
                    id={`id-indicator-${indicator.id}`}
                    labelText={getIndicatorLabel(indicator)}
                    checked={
                      watchAllFields?.indicators?.includes(indicator.id) &&
                      indicators?.some((item) => item.id === indicator.id)
                    }
                    onChange={(event, checked) => {
                      event.persist();
                      handleIndicatorOnChange(checked, indicator, event);
                    }}
                  />
                  {/* Admin link icon */}
                  {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
                  <Link
                    style={{ marginLeft: "5px" }}
                    onClick={() => openPopup(adminUrl)}
                  >
                    <FontAwesomeIcon
                      icon={faArrowUpRightFromSquare}
                      className="wfp--btn__icon cms-link-icon"
                    />
                  </Link>

                  {/* Info link icon */}
                  {indicator.url && (
                    <Link
                      style={{ marginLeft: "5px" }}
                      href={indicator.url}
                      target="_blank"
                    >
                      <FontAwesomeIcon
                        style={{
                          width: 15,
                          height: 15,
                          verticalAlign: "middle",
                        }}
                        icon={faCircleInfo}
                      />
                    </Link>
                  )}
                  {/* Drag & Drop icon */}
                  <div
                    className="d-flex"
                    style={{
                      alignItems: "center",
                      marginBottom: "1rem",
                      marginLeft: "10px",
                    }}
                  >
                    <FontAwesomeIcon
                      className="draggable-icon"
                      style={{ width: 14, height: 14 }}
                      icon={faGripVertical}
                    />
                  </div>
                </div>
              )}
            />
          </ListItem>
        </div>
      )}
    </Draggable>
  );
}

export default IndicatorList;
