import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { useForm } from "react-hook-form";
import { render, screen } from "../../utils/tests";
import IndicatorList from "./index";
import { createTestStore } from "../../redux/store";

const fakeIndicator = {
  id: 0,
  label: "TEST_LABEL",
  url: "TEST_URL",
};

window.initialState = {
  indicators: { data: [fakeIndicator] },
};

const store = createTestStore();

function getWrapper(store) {
  return function Wrapper({ children }) {
    return (
      <Provider store={store}>
        <DragDropContext>
          <Droppable>{() => children}</Droppable>
        </DragDropContext>
      </Provider>
    );
  };
}

function IndicatorListWithFormControl(props) {
  const { control } = useForm();

  return <IndicatorList control={control} {...props} />;
}

describe("IndicatorList", () => {
  it("should match snapshot", async () => {
    const store = createTestStore(window.initialState);
    const Wrapper = getWrapper(store);
    const { container } = render(
      <IndicatorListWithFormControl
        indicator={fakeIndicator}
        indicatorIndex={0}
      />,
      { wrapper: Wrapper }
    );
    expect(container).toMatchSnapshot();
  });

  it("checkbox shouldn't be checked", async () => {
    const store = createTestStore(window.initialState);
    const Wrapper = getWrapper(store);
    render(
      <IndicatorListWithFormControl
        indicator={fakeIndicator}
        indicatorIndex={0}
      />,
      { wrapper: Wrapper }
    );
    const checkbox = await screen.findByRole("checkbox");
    expect(checkbox).not.toBeChecked();
  });

  it("checkbox should be checked", async () => {
    const store = createTestStore(window.initialState);
    const Wrapper = getWrapper(store);
    render(
      <IndicatorListWithFormControl
        indicator={fakeIndicator}
        indicatorIndex={0}
        watchAllFields={{ indicators: [0] }}
      />,
      { wrapper: Wrapper }
    );
    const checkbox = await screen.findByRole("checkbox");
    expect(checkbox).toBeChecked();
  });
});
