import React from "react";
import "@testing-library/jest-dom";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { FormProvider } from "react-hook-form";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { render } from "../../utils/tests";
import SurveyWizard from "./index";
import { createTestStore } from "../../redux/store";

const store = createTestStore();

function Wrapper({ children }) {
  return (
    <MemoryRouter>
      <Provider store={store}>
        <FormProvider>{children}</FormProvider>
      </Provider>
    </MemoryRouter>
  );
}

describe("SurveyWizard", () => {
  it("should render", () => {
    const { container } = render(<SurveyWizard />, {
      wrapper: Wrapper,
    });
    expect(container).toMatchSnapshot();
  });
});
