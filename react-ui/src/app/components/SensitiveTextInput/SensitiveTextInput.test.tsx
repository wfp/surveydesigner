import React, { InputHTMLAttributes } from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "../../utils/tests";
import SensitiveTextInput from "./index";

describe("SensitiveTextInput", async () => {
  it("should match snapshot ", () => {
    const { container } = render(<SensitiveTextInput />);

    expect(container).toMatchSnapshot();
  });

  it("should toggle mask after clicking on button", () => {
    render(<SensitiveTextInput />);

    const textInput = screen.getByTestId<HTMLInputElement>("textinput");
    expect(textInput.type).toMatch("password");
    const button = screen.getByRole("button", { hidden: true });
    fireEvent.click(button);

    expect(textInput.type).toMatch("text");
  });
});
