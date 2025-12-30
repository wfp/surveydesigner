import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { useForm } from "react-hook-form";
import { render } from "../../utils/tests";
import IndicatorAreaListItem from "./index";
import { createTestStore } from "../../redux/store";
import { ModulesProvider } from "../../contexts/ModulesContext";

const fakeIndicator = {
  id: 0,
  label: "MOCK_LABEL",
  url: "MOCK_URL",
};

const fakeIndicatorArea = {
  id: 0,
  label: "MOCK_LABEL",
  url: "MOCK_LABEL",
  description: "MOCK_DESCRIPTION",
  indicators: [fakeIndicator],
};

const fakeCollapseAll = {
  run: false,
  isChecked: false,
};

window.initialState = {
  indicators: [fakeIndicator],
};

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

function IndicatorListWithFormControl(props) {
  const { control } = useForm();

  return <IndicatorAreaListItem control={control} {...props} />;
}

describe("IndicatorList", () => {
  it("should match snapshot", () => {
    const { container } = render(
      <IndicatorListWithFormControl
        indicatorArea={fakeIndicatorArea}
        collapseAll={{ isChecked: false, run: false }}
      />,
      { wrapper: Wrapper }
    );

    expect(container).toMatchSnapshot();
  });
});
