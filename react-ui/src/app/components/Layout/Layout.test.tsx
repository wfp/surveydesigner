import React from "react";
import '@testing-library/jest-dom/extend-expect';
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "../../utils/tests";
import Layout from "./index";
import { createTestStore } from "../../redux/store";

const store = createTestStore();

function Wrapper({ children }) {
  return (
    <MemoryRouter>
      <Provider store={store}>{children}</Provider>
    </MemoryRouter>
  );
}

describe("Layout", async () => {
  it("should match snapshot", () => {
    const { container } = render(
      <Layout title="TEST_TITLE" subTitle="TEST_SUBTITLE">
        TEST_CHILDREN
      </Layout>,
      { wrapper: Wrapper }
    );

    expect(container).toMatchSnapshot();
  });

  it("should set correct document title", () => {
    render(<Layout title="TEST_TITLE" />, { wrapper: Wrapper });

    expect(document.title).toMatchInlineSnapshot(
      '"TEST_TITLE | WFP Survey Designer"'
    );
  });

  it("shouldn't show loading indicator", async () => {
    render(<Layout />, { wrapper: Wrapper });

    const loadingIndicator = screen.queryByTestId("loading-indicator");

    expect(loadingIndicator).not.toBeInTheDocument();
  });

  it("should show loading indicator", async () => {
    const store = createTestStore({
      app: {
        isLoading: true,
      },
    });

    function Wrapper({ children }) {
      return (
        <MemoryRouter>
          <Provider store={store}>{children}</Provider>
        </MemoryRouter>
      );
    }

    render(<Layout />, { wrapper: Wrapper });

    const loadingIndicator = screen.getByTestId("loading-indicator");
    expect(loadingIndicator).toBeInTheDocument();
  });
});
