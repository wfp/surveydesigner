import React from "react";
import "@testing-library/jest-dom";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import { FormProvider, useForm } from "react-hook-form";
import { render, screen } from "../../utils/tests";
import SubmoduleListItem from "./index";

const fakeSubmodule = { id: 0 };

function SubmoduleListItemWithFormControl(props) {
  const { control } = useForm();

  return <SubmoduleListItem control={control} {...props} />;
}

function Wrapper({ children }) {
  return (
    <FormProvider>
      <DragDropContext>
        <Droppable>{() => children}</Droppable>
      </DragDropContext>
    </FormProvider>
  );
}

describe("SubmoduleListItem", () => {
  it("should match snapshot", () => {
    const { container } = render(
      <SubmoduleListItemWithFormControl
        submodule={fakeSubmodule}
        submodules={[fakeSubmodule.id]}
      />,
      { wrapper: Wrapper }
    );

    expect(container).toMatchSnapshot();
  });

  it("shouldn't be checked", async () => {
    render(
      <SubmoduleListItemWithFormControl
        submodule={fakeSubmodule}
        submodules={[]}
      />,
      { wrapper: Wrapper }
    );

    const checkbox = await screen.findByRole("checkbox");

    expect(checkbox).not.toBeChecked();
  });
});
