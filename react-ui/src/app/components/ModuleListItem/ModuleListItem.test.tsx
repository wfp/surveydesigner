import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { useForm } from "react-hook-form";
import { render } from "../../utils/tests";
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
});
