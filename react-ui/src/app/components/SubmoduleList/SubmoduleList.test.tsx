import React from "react";
import "@testing-library/jest-dom";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { Provider } from "react-redux";
import { useForm } from "react-hook-form";
import { vi } from "vitest";
import SubmoduleList from "./index";
import { render } from "../../utils/tests";
import { createTestStore } from "../../redux/store";
import { ModulesProvider } from "../../contexts/ModulesContext";

const fakeSubQuestions = [{ suffix: { name: "MOCK_SUFFIX" } }];

const fakeSubmodule = {
  id: 0,
  root_questions: [
    {
      sub_questions: fakeSubQuestions,
    },
  ],
};

const fakeModule = { id: 0, submodules: [fakeSubmodule] };

window.initialState = {
  modules: { data: [fakeModule] },
};

const store = createTestStore();

function Wrapper({ children }) {
  return (
    <Provider store={store}>
      <ModulesProvider
        initialValue={{
          modules_order: [fakeModule.id],
          submodules_order: [[fakeSubmodule.id]],
        }}
      >
        <DragDropContext>
          <Droppable droppableId="0">{() => children}</Droppable>
        </DragDropContext>
      </ModulesProvider>
    </Provider>
  );
}

function SubmoduleListWithFormControl(props) {
  const { control } = useForm();

  return <SubmoduleList control={control} {...props} />;
}

describe("SubmoduleList", () => {
  it("should match snapshot", () => {
    const mockGetRootQuestionsCount = vi.fn((submodules) => submodules.length);

    const { container } = render(
      <SubmoduleListWithFormControl
        submodules={[fakeSubmodule]}
        submodulesMap={{
          0: {
            next: {
              next: [{ next: [] }],
              real_item: { name: "MOCK_NAME" },
              sub_questions: fakeSubQuestions,
            },
          },
        }}
        selectedOptions={new Set()}
        submodulesData={{
          isLoading: true,
        }}
        setSelectAll={vi.fn()}
        selectAll={{ isChecked: true }}
        collapseAll={{ isChecked: true }}
        subQuestions={[]}
        setSubQuestions={vi.fn()}
        getRootQuestionsCount={mockGetRootQuestionsCount}
      />,
      { wrapper: Wrapper }
    );

    expect(container).toMatchSnapshot();
  });
});
