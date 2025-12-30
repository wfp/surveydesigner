import React, { useRef, useState } from "react";
import { Button, DateRangePicker } from "@wfp/react";
import {
  useForm,
  Controller,
  FormProvider,
  FieldValues,
} from "react-hook-form";
import { Column } from "react-table";
import { useTranslation } from "react-i18next";
import ReactDatePicker from "react-datepicker";

interface FilterInterface {
  filters: {
    [key: string]: unknown;
  };
  updateFilters: (newFilters: object) => void;
  clearFilters: () => void;
  columns: Column<any>[];
  showFilters: boolean;
  setShowFilters: (showFilters: boolean) => void;
}

function Filters({
  filters,
  updateFilters,
  clearFilters,
  columns,
  showFilters,
  setShowFilters,
}: FilterInterface) {
  const { t } = useTranslation();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [focusedInput, setFocusedInput] = useState(null);
  const methods = useForm<FieldValues>({
    defaultValues: filters,
  });
  const { handleSubmit, control, reset } = methods;

  const onSubmit = (values: FieldValues) => {
    const updatedValues = {
      ...values,
      start_date: startDate,
      end_date: endDate,
    };
    updateFilters(updatedValues);
  };

  return (
    <div className="filter-container">
      <Button
        small
        className="filter-button"
        onClick={() => setShowFilters(!showFilters)}
      >
        {!showFilters ? t("filters.show") : t("filters.hide")}
      </Button>

      {showFilters && (
        <FormProvider {...methods}>
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="filter-options">
              {columns
                .filter((column) => column.accessor !== "actions")
                .map((column) => {
                  if (column.accessor === "sortable_updated_at") {
                    // Render the DateRangePicker for the "sortable_updated_at" field
                    return (
                      <div key={column.accessor}>
                        <label>{t("surveyTable.lastSavedDate")}</label>
                        <DateRangePicker
                          datePicker={ReactDatePicker}
                          startDate={startDate}
                          endDate={endDate}
                          setStartDate={(newDate) => setStartDate(newDate)}
                          setEndDate={(newDate) => setEndDate(newDate)}
                        />
                      </div>
                    );
                  } else {
                    // Render a regular text input for other fields
                    return (
                      <div key={column.accessor}>
                        <label htmlFor={column.accessor}>
                          {column.Header as string}
                        </label>
                        <Controller
                          render={({ field }) => <input {...field} />}
                          control={control}
                          name={column.accessor as string}
                          defaultValue=""
                        />
                      </div>
                    );
                  }
                })}
            </div>
            <div className="filterActionButtons">
              <Button
                kind="secondary"
                small
                onClick={() => {
                  reset(
                    columns.reduce((acc, column) => {
                      acc[column.accessor] = "";
                      return acc;
                    }, {}),
                  );
                  clearFilters();
                }}
              >
                {t("filters.clear")}
              </Button>
              <Button
                small
                onClick={() => buttonRef.current && buttonRef.current.click()}
              >
                {t("filters.apply")}
              </Button>
            </div>
            <button type="submit" ref={buttonRef} style={{ display: "none" }}>
              none
            </button>
          </form>
        </FormProvider>
      )}
    </div>
  );
}

export default Filters;
