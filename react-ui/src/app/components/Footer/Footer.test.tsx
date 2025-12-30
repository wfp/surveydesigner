import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "../../utils/tests";
import Footer from "./index";

describe("Footer", async () => {
  it("should render footer", () => {
    render(<Footer />, {});
    const year = new Date().getFullYear();
    expect(
      screen.getByText(`${year} ©footer.wfp`)
    ).toBeInTheDocument();
  });

  it("should match snapshot", () => {
    const { container } = render(<Footer />, {});
    expect(container).toMatchSnapshot();
  });
});
