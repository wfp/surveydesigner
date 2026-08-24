import React from "react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "../../utils/tests";
import { createTestStore } from "../../redux/store";
import Review from "./index";
import { API } from "../../utils";
import userEvent from "@testing-library/user-event";

vi.mock("../SubmoduleList", () => ({
  default: () => null,
}));

vi.mock("../../contexts/ModulesContext", () => ({
  useModules: () => ({
    current: {
      modules_order: [],
      submodules_order: {},
      indicator_areas_order: [],
      indicators_order: {},
    },
  }),
}));
vi.mock("../../utils", async () => {
  const actual = await vi.importActual("../../utils");
  return {
    ...actual,
    API: {
      post: vi.fn(),
    },
  };
});

const previewValidationError = {
  response: {
    status: 400,
    data: {
      valid: false,
      errors: [
        {
          code: "RELEVANT_VALIDATION_ERROR",
          layer: "compatibility",
          severity: "error",
          message: "The same validation error",
        },
      ],
      warnings: [],
    },
  },
};

function renderReview() {
  const store = createTestStore({
    submodules: {
      isLoading: false,
      error: null,
      data: [],
      selectedOptions: [],
    },
  });

  return render(
    <Review
      next={vi.fn()}
      numberOfQuestionsToBeGenerated={0}
      selectAll={false}
      setSelectAll={vi.fn()}
      collapseAll={false}
      setCollapseAll={vi.fn()}
      setNumberOfQuestionsToBeGenerated={vi.fn()}
      selectedSurveyToEdit={null}
    />,
    {
      wrapper: ({ children }) => <Provider store={store}>{children}</Provider>,
    },
  );
}

describe("Review preview notifications", () => {
  beforeEach(() => {
    vi.mocked(API.post).mockReset();
    vi.mocked(API.post).mockRejectedValue(previewValidationError as never);
  });

  it("shows the same validation error again after it is dismissed", async () => {
    const user = userEvent.setup();
    const { getByRole, getByText, queryByRole } = renderReview();
    const previewButton = getByText("review.previewSurvey");

    await user.click(previewButton);
    await waitFor(() => expect(getByRole("api_errors")).toBeVisible());

    const closeButton = getByRole("api_errors").querySelector("button");
    expect(closeButton).not.toBeNull();
    await user.click(closeButton as HTMLElement);
    expect(queryByRole("api_errors")).not.toBeInTheDocument();

    await user.click(previewButton);
    await waitFor(() => expect(getByRole("api_errors")).toBeVisible());
    expect(getByRole("api_errors")).toHaveTextContent(
      "The same validation error",
    );
    expect(API.post).toHaveBeenCalledTimes(2);
  });
});
