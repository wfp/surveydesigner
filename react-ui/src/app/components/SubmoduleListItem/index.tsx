import React from "react";
import { useTranslation } from "react-i18next";
import { Draggable } from "react-beautiful-dnd";
import { Controller } from "react-hook-form";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faCircleInfo,
  faGripVertical,
} from "@fortawesome/free-solid-svg-icons";

import { Checkbox, Link, ListItem, Tooltip } from "@wfp/react";

import { getSubmoduleCmsUrl, openPopup } from "../../utils/url";
import { Submodule } from "../../types/api";
import { SubmoduleListItemProps } from "./SubmoduleListItem.interface";

function SubmoduleListItem({
  submodule,
  submoduleIndex,
  control,
  submodules,
  handleSubmoduleChange,
  isSelectedByIndicator,
  selectedIndicatorSubmoduleIdMap,
  selectedIndicatorMatchingSubmoduleIdMap,
}: SubmoduleListItemProps) {
  const { t } = useTranslation();

  function getSubmoduleLabel(submodule: Submodule) {
    let label = submodule.is_mandatory ? (
      <>
        {submodule.label} <span className="required">*</span>
      </>
    ) : (
      submodule.label
    );
    label = <span className="survey-list-row__label-text">{label}</span>;
    if (!submodule.description) {
      return label;
    }

    return (
      <Tooltip
        content={submodule.description}
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
  const pluralize = (count: number, noun: string, suffix = "s") =>
    `${noun}${count !== 1 ? suffix : ""}`;
  const adminUrl = getSubmoduleCmsUrl(submodule);

  const renderSubmoduleText = (
    submoduleId: number,
    selectedIndicatorMatchingSubmoduleIdMap: Record<number, string[]>,
    selectedIndicatorSubmoduleIdMap: Record<number, string[]>,
  ) => {
    const matchingIndicators =
      selectedIndicatorMatchingSubmoduleIdMap[submoduleId] || [];
    const includedIndicators =
      selectedIndicatorSubmoduleIdMap[submoduleId] || [];
    const indicatorsList = matchingIndicators.length
      ? matchingIndicators.join(", ")
      : includedIndicators.join(", ");
    if (matchingIndicators.length) {
      const indicatorCount = matchingIndicators.length;
      const lastWord = indicatorsList.split(" ").pop();
      const shouldIncludeSuffix = !/^(indicator|Indicator)$/.test(
        lastWord ?? "",
      );
      const indicatorText = shouldIncludeSuffix
        ? t("submoduleListItem.indicatorPlural", { indicatorsList })
        : t("submoduleListItem.indicatorSingular", { indicatorsList });
      return indicatorText;
    }
    if (includedIndicators.length) {
      return t("submoduleListItem.partiallyIncluded", { indicatorsList });
    }
    return t("submoduleListItem.noIndicatorsIncluded");
  };

  return (
    <Draggable
      draggableId={`submodule-${submodule.id.toString()}`}
      index={submoduleIndex}
    >
      {(submoduleProvidedNext, submoduleSnapshot) => (
        <div
          className={
            submoduleSnapshot.isDragging ? "greyBackground" : "whiteBackground"
          }
          {...submoduleProvidedNext.draggableProps}
          {...submoduleProvidedNext.dragHandleProps}
          ref={submoduleProvidedNext.innerRef}
        >
          <ListItem key={submodule.id} className="submodule-item">
            <Controller
              name="submodules"
              control={control}
              render={({ field: { onChange, value } }) => (
                <div>
                  <div className="survey-list-row">
                    <Checkbox
                      id={`id-submodule-${submodule.id}`}
                      labelText={getSubmoduleLabel(submodule)}
                      wrapperClassName="survey-list-row__checkbox"
                      checked={submodules.includes(submodule.id)}
                      onChange={(event, checked, customId) => {
                        event.persist();
                        handleSubmoduleChange(checked, submodule, event);
                      }}
                    />

                    {/* Admin link icon */}
                    <div className="survey-list-row__actions">
                      <Link
                        className="survey-list-row__icon-link"
                        onClick={() => openPopup(adminUrl)}
                      >
                        <FontAwesomeIcon
                          icon={faArrowUpRightFromSquare}
                          className="wfp--btn__icon cms-link-icon"
                        />
                      </Link>

                      {/* Info link icon */}
                      {submodule.url && (
                        <Link
                          className="survey-list-row__icon-link"
                          href={submodule.url}
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
                      <div className="survey-list-row__drag">
                        <FontAwesomeIcon
                          className="draggable-icon"
                          style={{ width: 14, height: 14 }}
                          icon={faGripVertical}
                        />
                      </div>
                    </div>
                  </div>
                  {isSelectedByIndicator && (
                    <div className="survey-list-row__status">
                      {renderSubmoduleText(
                        submodule.id,
                        selectedIndicatorMatchingSubmoduleIdMap,
                        selectedIndicatorSubmoduleIdMap,
                      )}
                    </div>
                  )}
                </div>
              )}
            />
          </ListItem>
        </div>
      )}
    </Draggable>
  );
}

export default SubmoduleListItem;
