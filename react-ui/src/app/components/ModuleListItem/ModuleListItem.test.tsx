import React from "react";
import "@testing-library/jest-dom";
import { vi } from "vitest";
import { Provider } from "react-redux";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { useForm } from "react-hook-form";
import { render, screen, waitFor } from "../../utils/tests";
import ModuleListItem from "./index";
import { createTestStore } from "../../redux/store";
import { ModulesProvider } from "../../contexts/ModulesContext";

const fakeModule = {
  id: 0,
  label: "MOCK_LABEL",
  url: "MOCK_URL",
  description: "MOCK_DESCRIPTION",
  submodules: [],
};

const fakeWatchAllFields = {
  indicators: [],
};

const fakeCollapseAll = {
  isChecked: false,
  run: false,
};

window.initialState = {};

const store = createTestStore();

function Wrapper({ children }) {
  return (
    <Provider store={store}>
      <ModulesProvider>
        <DragDropContext>
          <Droppable>{() => children}</Droppable>
        </DragDropContext>
      </ModulesProvider>
    </Provider>
  );
}

function CollapsedModuleWrapper({ children }) {
  return (
    <Provider store={store}>
      <ModulesProvider
        initialValue={{
          collapsed: new Set([fakeModule.id]),
          modules_order: [fakeModule.id],
          modules_count: 1,
          submodules_order: { [fakeModule.id]: [5] },
          submodules_count: 1,
          indicator_areas_order: [],
          indicators_order: {},
          review_modules_collapsed: new Set(),
          review_submodules_collapsed: new Set(),
        }}
      >
        <DragDropContext>
          <Droppable>{() => children}</Droppable>
        </DragDropContext>
      </ModulesProvider>
    </Provider>
  );
}

function ModuleListItemWithFormControl(props) {
  const { control } = useForm();

  return <ModuleListItem control={control} {...props} />;
}

describe("IndicatorList", () => {
  it("should match snapshot", () => {
    const { container } = render(
      <ModuleListItemWithFormControl
        module={fakeModule}
        watchAllFields={fakeWatchAllFields}
        collapseAll={fakeCollapseAll}
      />,
      { wrapper: Wrapper }
    );

    expect(container).toMatchSnapshot();
  });

  it("expands a collapsed module to reveal the validation target", async () => {
    render(
      <ModuleListItemWithFormControl
        module={{ ...fakeModule, submodules: [{ id: 5 }] }}
        index={0}
        submodules={[]}
        watchAllFields={fakeWatchAllFields}
        collapseAll={fakeCollapseAll}
        setCollapseAll={vi.fn()}
        handleSubmoduleChange={vi.fn()}
        validationSubmoduleId={5}
      />,
      { wrapper: CollapsedModuleWrapper },
    );

    await waitFor(() =>
      expect(screen.getByTestId("submodule-draggable-5")).toHaveClass(
        "submodule-item--validation-error",
      ),
    );
  });
});
