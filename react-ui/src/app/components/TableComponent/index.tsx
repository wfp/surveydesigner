import React from "react";
import { Column, usePagination, useSortBy, useTable } from "react-table";
import { Pagination, Table } from "@wfp/react";

interface Props {
  data: any[];
  columns: Column<any>[];
  defaultPageSize?: number;
  showPagination?: boolean;
  totalItems?: number;
  showSort?: boolean;
  loadPage?: (filters: { [key: string]: string }) => void;
  sortBy?: { id: string; desc: boolean }[];
  emptyState?: React.ReactNode;
}

export function TableComponent({
  data,
  columns,
  defaultPageSize = 10,
  showPagination = true,
  totalItems,
  showSort = false,
  loadPage,
  sortBy,
  emptyState,
}: Props) {
  const memoColumns = React.useMemo(
    () =>
      columns && columns.length
        ? columns.map((column, index) => ({
            ...column,
            id: `id_${index}`,
            Header:
              typeof column.Header === "object"
                ? column.Header
                : (column.Header as string),
          }))
        : [],
    [columns],
  );
  const memoSortBy = React.useMemo(
    () =>
      sortBy && sortBy.length
        ? sortBy.map((sortingObject) => {
            const conColumn = memoColumns?.find(
              (column) => column.accessor === sortingObject.id,
            );
            return {
              ...sortingObject,
              id: conColumn ? conColumn.id : sortingObject.id,
            };
          })
        : [],
    [sortBy, memoColumns],
  );

  const dataArray = Array.isArray(data) ? data : [];
  const memoData = React.useMemo(() => dataArray, [data]);
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    page,
    gotoPage,
    setPageSize,
    state: { pageIndex, pageSize },
  } = useTable(
    {
      data: memoData,
      columns: memoColumns,
      initialState: {
        pageIndex: 0,
        pageSize: defaultPageSize,
        sortBy: memoSortBy,
      },
      disableSortBy: !sortBy,
    },
    useSortBy,
    usePagination,
  );

  const changePage: any = (page: { page: number; pageSize: number }) => {
    gotoPage(page.page - 1);

    if (pageSize !== page.pageSize) {
      setPageSize(page.pageSize);
    }
    if (loadPage) loadPage({ page_size: page.pageSize, page: page.page });
  };

  return (
    <>
      <Table {...getTableProps()}>
        <thead>
          {headerGroups.map((headerGroup: any) => {
            const { key: headerGroupKey, ...headerGroupProps } =
              headerGroup.getHeaderGroupProps();
            return (
              <tr key={headerGroupKey} {...headerGroupProps}>
                {headerGroup.headers.map((column) => {
                  const { key: headerKey, ...headerProps } =
                    column.getHeaderProps(column.getSortByToggleProps());
                  const { key: sortKey, ...sortProps } =
                    column.getSortByToggleProps();
                  return (
                    <th
                      key={headerKey}
                      {...headerProps}
                      className="survey-table-header"
                      style={{ width: column.width }}
                    >
                      {showSort && column.canSort ? (
                        <div
                          {...sortProps}
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            justifyContent: "space-between",
                          }}
                        >
                          <div>{column.render("Header")}</div>
                          <div>
                            {column.isSorted
                              ? column.isSortedDesc
                                ? "desc"
                                : "asc"
                              : "-"}
                          </div>
                        </div>
                      ) : (
                        column.render("Header")
                      )}
                    </th>
                  );
                })}
              </tr>
            );
          })}
        </thead>
        <tbody {...getTableBodyProps()}>
          {page.length === 0 && (
            <tr>
              <td colSpan={memoColumns.length} className="survey-table-cell">
                {emptyState}
              </td>
            </tr>
          )}
          {page.map((row) => {
            prepareRow(row);
            const { key: rowKey, ...rowProps } = row.getRowProps();
            return (
              <tr key={rowKey} {...rowProps}>
                {row.cells.map((cell) => {
                  const { key: cellKey, ...cellProps } = cell.getCellProps();
                  return (
                    <td
                      key={cellKey}
                      {...cellProps}
                      className="survey-table-cell"
                    >
                      {cell.render("Cell")}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </Table>
      {showPagination && page.length > 0 && (
        <Pagination
          pageSize={pageSize}
          pageSizes={[10, 20, 30]}
          page={pageIndex + 1}
          totalItems={totalItems || (Array.isArray(data) ? data.length : 0)}
          onChange={changePage}
        />
      )}
    </>
  );
}

export default TableComponent;
