import { describe, expect, it } from "vitest";

import { getApiErrorMessages, getApiErrorSummary } from "./apiError";

describe("api error helpers", () => {
  it("uses the fallback when the response payload contains no messages", () => {
    expect(
      getApiErrorMessages({ response: { data: {} } }, "Something went wrong."),
    ).toEqual(["Something went wrong."]);
    expect(
      getApiErrorMessages({ response: { data: [] } }, "Something went wrong."),
    ).toEqual(["Something went wrong."]);
    expect(
      getApiErrorSummary({ response: { data: "" } }, "Something went wrong."),
    ).toBe("Something went wrong.");
  });

  it("returns extracted messages when the response payload is useful", () => {
    expect(
      getApiErrorSummary(
        { response: { data: { detail: "File upload failed." } } },
        "Something went wrong.",
      ),
    ).toBe("detail: File upload failed.");
  });
});
