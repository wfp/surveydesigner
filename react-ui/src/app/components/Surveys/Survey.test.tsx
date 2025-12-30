import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { render } from "../../utils/tests";
import Survey from "./index";
import { createTestStore } from "../../redux/store";

describe("Survey", () => {
  it("should match snapshot", () => {
    window.initialState = {
      surveys: {
        isLoading: false,
        data: {
          categories: [],
          modes: [],
        },
      },
      organizations: {
        isLoading: false,
        data: [],
      },
    };

    const store = createTestStore();

    const { container } = render(<Survey next={vi.fn()} />, {
      wrapper: ({ children }) => (
        <MemoryRouter>
          <Provider store={store}>{children}</Provider>
        </MemoryRouter>
      ),
    });

    expect(container).toMatchSnapshot();
  });

  it("should render loading indicator", () => {
    window.initialState = {
      surveys: {
        isLoading: true,
      },
      organizations: {
        isLoading: true,
      },
    };

    const store = createTestStore();

    const { container } = render(<Survey next={vi.fn()} />, {
      wrapper: ({ children }) => (
        <MemoryRouter>
          <Provider store={store}>{children}</Provider>
        </MemoryRouter>
      ),
    });

    expect(container).toMatchSnapshot();
  });
});
