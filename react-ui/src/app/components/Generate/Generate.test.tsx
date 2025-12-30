import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import {API} from "../../utils";
import { vi } from "vitest";
import { render } from "../../utils/tests";
import Generate from "./index";
import { createTestStore } from "../../redux/store";

const fakeUser = { id: 0 };

const store = createTestStore();

function Wrapper({ children }) {
  return <Provider store={store}>{children}</Provider>;
}

vi.mock("../../utils");

describe("Generate", () => {
  API.get.mockResolvedValue({
    data: fakeUser,
  });

  it("should match snapshot", async () => {
    const { container } = render(<Generate next={vi.fn()} />, {
      wrapper: Wrapper,
    });

    expect(container).toMatchSnapshot();
  });
});
