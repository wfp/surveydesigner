import React, {
  useCallback,
  useImperativeHandle,
  useMemo,
  useState,
  useEffect,
} from "react";

import { Button, Loading } from "@wfp/react";
import { ButtonKind } from "@wfp/react/src/types/utils";
import { useDispatch } from "react-redux";
import { CellProps, Column } from "react-table";
import { useTranslation } from "react-i18next";
import TableComponent from "../TableComponent";
import Filters from "../Filters";
import { fetchSavedSurveys } from "../../redux/actions/savedSurveysActions";

const loadingContent = (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "100%",
    }}
  >
    <Loading withOverlay={false} />
  </div>
);

interface ActionComponentInterface {
  text: string;
  Component: any;
  kind: ButtonKind;
  onClick: (arg0: unknown) => unknown;
  id: string;
}

export interface ActionsInterface {
  edit: (id: number) => void;
  delete: (id: number) => void;
  share: (id: number) => void;
}

export const generateActions = (
  original: { uuid: number },
  actions: ActionsInterface,
  t: (string: string) => string,
) => {
  const actionComponents: ActionComponentInterface[] = [
    {
      text: t("actions.edit"),
      Component: Button,
      kind: "primary",
      onClick: () => actions.edit(original.uuid),
      id: `edit-${original.uuid}`,
    },
    {
      text: t("actions.share"),
      Component: Button,
      kind: "primary",
      onClick: () => actions.share(original.uuid),
      id: `share-${original.uuid}`,
    },
    {
      text: t("actions.delete"),
      Component: Button,
      kind: "danger--primary",
      onClick: () => actions.delete(original.uuid),
      id: `delete-${original.uuid}`,
    },
  ];

  return (
    <div className="surveyActionsWrapper">
      {actionComponents.map(({ Component, text, id, ...props }) => (
        <div key={`action--wrapper--${id}`} className="survey-action">
          <Component key={`${typeof Component}-${id}`} {...props} small>
            {text}
          </Component>
        </div>
      ))}
    </div>
  );
};

type ColumnData = {
  id: number;
  name: string;
  organizations: string;
  survey_category: string;
  survey_type: string;
  survey_mode: string;
  attributes: string;
  updated_at: string;
  sortable_updated_at: string;
  actions: string;
};

const SurveyTable = React.forwardRef(
  (
    {
      data = [],
      isFetching,
      count,
      actions,
      onCreateSurvey,
    }: {
      data?: unknown[];
      isFetching: boolean;
      count: number;
      actions: ActionsInterface;
      onCreateSurvey?: () => void;
    },
    ref,
  ) => {
    const { t } = useTranslation();
    const dispatch = useDispatch();

    const [filters, setFilters] = useState({});
    const [showFilters, setShowFilters] = useState(false);

    const loadPage = useCallback(
      (filterParams: object) => {
        dispatch(fetchSavedSurveys(filterParams));
      },
      [dispatch],
    );

    useEffect(() => {
      loadPage(filters);
    }, [filters, loadPage]);

    const updateFilters = (newFilters: object) => {
      setFilters(newFilters);
    };

    const clearFilters = () => {
      setFilters({});
    };

    useImperativeHandle(ref, () => ({
      clearFilters,
    }));

    const columns: Column<ColumnData>[] = [
      {
        Header: t("surveyTable.name"),
        accessor: "name",
      },
      {
        Header: t("surveyTable.organizations"),
        accessor: "organizations",
      },
      {
        Header: t("surveyTable.category"),
        accessor: "survey_category",
      },
      {
        Header: t("surveyTable.type"),
        accessor: "survey_type",
      },
      {
        Header: t("surveyTable.mode"),
        accessor: "survey_mode",
      },
      {
        Header: t("surveyTable.context"),
        accessor: "attributes",
      },
      {
        Header: t("surveyTable.lastSavedDate"),
        accessor: "sortable_updated_at", // Use sortable_updated_at for sorting
        Cell: ({ row }) => (
          // Display formatted_updated_at
          <span>{row.original.updated_at}</span>
        ),
      },
      {
        Header: "",
        accessor: "actions",
        Cell: (d: CellProps<ColumnData>) =>
          generateActions(d.row.original, actions, t),
        disableSortBy: true,
      },
    ];

    const filtersProps = {
      columns,
      filters,
      showFilters,
      setShowFilters,
      setFilters,
      updateFilters,
      clearFilters,
    };

    const hasActiveFilters = useMemo(
      () =>
        Object.values(filters).some(
          (value) =>
            value !== null &&
            value !== undefined &&
            !(typeof value === "string" && value.trim() === ""),
        ),
      [filters],
    );

    const emptyState = (
      <div className="survey-table-empty-state">
        <h3>
          {hasActiveFilters
            ? t(
                "surveyTable.empty.filteredTitle",
                "No saved surveys match your filters",
              )
            : t("surveyTable.empty.title", "No saved surveys yet")}
        </h3>
        <p>
          {hasActiveFilters
            ? t(
                "surveyTable.empty.filteredDescription",
                "Clear the filters or adjust your search to see saved surveys.",
              )
            : t(
                "surveyTable.empty.description",
                "Create a survey to save it here and return to it later.",
              )}
        </p>
        {hasActiveFilters ? (
          <Button
            kind="secondary"
            small
            onClick={() => {
              setShowFilters(false);
              clearFilters();
            }}
          >
            {t("filters.clear")}
          </Button>
        ) : (
          onCreateSurvey && (
            <Button small onClick={onCreateSurvey}>
              {t("surveyWizard.createSurvey")}
            </Button>
          )
        )}
      </div>
    );

    if (isFetching) {
      return loadingContent;
    }

    return (
      <div>
        <Filters {...filtersProps} />
        <div className="table survey-table-wrapper">
          <TableComponent
            columns={columns}
            data={data}
            showPagination
            totalItems={count}
            sortBy={[{ id: "sortable_updated_at", desc: true }]}
            showSort
            emptyState={emptyState}
          />
        </div>
      </div>
    );
  },
);

SurveyTable.displayName = "SurveyTable";

export default SurveyTable;
