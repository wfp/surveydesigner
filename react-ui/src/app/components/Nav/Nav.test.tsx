import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { render } from "../../utils/tests";
import Nav from "./index";
import { createTestStore } from "../../redux/store";

describe("Nav", async () => {
  it("should render when logged in", () => {
    window.initialState = {
      auth: {
        is_logged: true,
        user: {
          display_name: "MOCK_DISPLAY_NAME",
          can_access_cms: true,
          read_only_member: true,
        },
      },
    };

    const store = createTestStore();

    const { container } = render(<Nav />, {
      wrapper: ({ children }) => (
        <MemoryRouter>
          <Provider store={store}>{children}</Provider>
        </MemoryRouter>
      ),
    });

    expect(container).toMatchSnapshot();
  });

  it("should render when logged out", () => {
    window.initialState = {
      auth: {
        is_logged: false,
        user: {
          display_name: "MOCK_DISPLAY_NAME",
          can_access_cms: true,
          read_only_member: true,
        },
      },
    };

    const store = createTestStore();

    const { container } = render(<Nav />, {
      wrapper: ({ children }) => (
        <MemoryRouter>
          <Provider store={store}>{children}</Provider>
        </MemoryRouter>
      ),
    });

    expect(container).toMatchSnapshot();
  });
});
