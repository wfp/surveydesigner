import React from "react";
import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router-dom";
import { render } from "../../utils/tests";
import LandingPage from "./index";

const originalEnv = import.meta.env.VITE_APP_API_ENDPOINT;

describe("LandingPage", async () => {
  beforeEach(() => {
    import.meta.env.VITE_APP_API_ENDPOINT = "";
  });

  afterEach(() => {
    import.meta.env.VITE_APP_API_ENDPOINT = originalEnv;
  });

  it("should match snapshot", () => {
    const { container } = render(<LandingPage />, { wrapper: MemoryRouter });

    expect(container).toMatchSnapshot();
  });
});
