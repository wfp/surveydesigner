import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { render } from "../../utils/tests";
import Notification from "./index";
import { createTestStore } from "../../redux/store";

describe("Notification", async () => {
  it("shouldn't show notification", () => {
    window.initialState = {
      notification: {
        show: false,
      },
    };

    const store = createTestStore();

    const { container } = render(<Notification />, {
      wrapper: ({ children }) => <Provider store={store}>{children}</Provider>,
    });

    expect(container).toMatchSnapshot();
  });

  it("should match snapshot ", () => {
    window.initialState = {
      notification: {
        kind: "success",
        title: "MOCK_TITLE",
        msg: "MOCK_MESSAGE",
        show: true,
      },
    };

    const store = createTestStore();

    const { container } = render(<Notification />, {
      wrapper: ({ children }) => <Provider store={store}>{children}</Provider>,
    });

    expect(container).toMatchSnapshot();
  });
});
