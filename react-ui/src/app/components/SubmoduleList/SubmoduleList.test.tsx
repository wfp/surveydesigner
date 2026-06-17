import React from "react";
import "@testing-library/jest-dom";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { Provider } from "react-redux";
import { useForm } from "react-hook-form";
import { vi } from "vitest";
import SubmoduleList from "./index";
import { render, waitFor } from "../../utils/tests";
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

const getPreloadedState = () => ({
  modules: { data: [fakeModule], error: null, isLoading: false },
});

function createWrapper(testStore = createTestStore(getPreloadedState())) {
  return function Wrapper({ children }) {
    return (
      <Provider store={testStore}>
        <ModulesProvider
          initialValue={{
            modules_order: [fakeModule.id],
            submodules_order: { [fakeModule.id]: [fakeSubmodule.id] },
          }}
        >
          <DragDropContext>
            <Droppable droppableId="0">{() => children}</Droppable>
          </DragDropContext>
        </ModulesProvider>
      </Provider>
    );
  };
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
      { wrapper: createWrapper() }
    );

    expect(container).toMatchSnapshot();
  });

  it("does not auto-select required groups when disabled", async () => {
    const requiredSubQuestion = {
      id: 123,
      suffix: { name: "MOCK_SUFFIX" },
      submodule: fakeSubmodule.id,
    };
    const requiredItem = {
      id: "id-0-required",
      display: "Required group",
      real_item: { name: "MOCK_NAME" },
      required: true,
      sub_questions: [requiredSubQuestion],
      next: {},
    };
    const testStore = createTestStore({
      ...getPreloadedState(),
      submodules: {
        data: [],
        error: null,
        isLoading: false,
        selectedOptions: [],
      },
    });
    const setNumberOfQuestionsToBeGenerated = vi.fn();
    const setSubQuestions = vi.fn();

    render(
      <SubmoduleListWithFormControl
        autoSelectRequired={false}
        submodules={[fakeSubmodule]}
        submodulesMap={{ 0: { requiredItem } }}
        selectedOptions={new Set()}
        submodulesData={{ isLoading: false }}
        setSelectAll={vi.fn()}
        selectAll={{ isChecked: false, run: false }}
        collapseAll={{ isChecked: false, run: false }}
        subQuestions={[]}
        setSubQuestions={setSubQuestions}
        setNumberOfQuestionsToBeGenerated={setNumberOfQuestionsToBeGenerated}
        getRootQuestionsCount={vi.fn(() => 0)}
      />,
      { wrapper: createWrapper(testStore) }
    );

    await waitFor(() =>
      expect(setNumberOfQuestionsToBeGenerated).toHaveBeenCalled()
    );
    expect(testStore.getState().submodules.selectedOptions).toEqual([]);
    expect(setSubQuestions).not.toHaveBeenCalled();
  });
});
