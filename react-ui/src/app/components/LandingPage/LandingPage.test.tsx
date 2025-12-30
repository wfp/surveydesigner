import React from "react";
import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router-dom";
import { render } from "../../utils/tests";
import LandingPage from "./index";

describe("LandingPage", async () => {
  it("should match snapshot", () => {
    const { container } = render(<LandingPage />, { wrapper: MemoryRouter });

    expect(container).toMatchSnapshot();
  });
});
