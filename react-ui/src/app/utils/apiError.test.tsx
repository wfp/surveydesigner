import {
  formatValidationIssues,
  getApiErrorStatus,
  getApiErrorSummary,
  getApiErrorTitle,
  parseApiError,
  parseValidationWarningsHeader,
} from "./apiError";

describe("API error handling", () => {
  it("preserves generic nested error formatting", () => {
    const error = {
      response: {
        status: 400,
        data: {
          message: "Request failed",
          detail: "The survey could not be published.",
          fields: { name: ["This field is required."] },
        },
      },
    };

    const summary = getApiErrorSummary(error);
    expect(summary).toContain("Request failed");
    expect(summary).toContain("fields.name: This field is required.");
    expect(getApiErrorTitle(error, "Publish failed")).toBe("Publish failed");
  });

  it("parses structured validation JSON returned as an Axios Blob", async () => {
    const parsed = await parseApiError({
      response: {
        status: 400,
        data: new Blob([
          JSON.stringify({
            valid: false,
            artifact_hash: "sha256:test",
            errors: [
              {
                code: "PYXFORM_CONVERSION_ERROR",
                layer: "pyxform",
                severity: "error",
                message: "Unknown question type",
                sheet: "survey",
                column: "type",
                row: 4,
              },
            ],
            warnings: [],
            validator: { pyxform: "4.5.0", compatibility: "1.0" },
          }),
        ]),
      },
    });

    expect(getApiErrorStatus(parsed)).toBe(400);
    expect(getApiErrorTitle(parsed)).toBe("Survey validation failed");
    expect(getApiErrorSummary(parsed)).toContain(
      "[PYXFORM_CONVERSION_ERROR] Unknown question type (sheet survey, column type, row 4)",
    );
  });

  it("distinguishes validator unavailability with HTTP 503", async () => {
    const parsed = await parseApiError({
      response: {
        status: 503,
        data: new Blob([
          JSON.stringify({
            valid: false,
            artifact_hash: "sha256:test",
            errors: [
              {
                code: "VALIDATOR_UNAVAILABLE",
                layer: "validator",
                severity: "error",
                message: "Validator unavailable",
              },
            ],
            warnings: [],
            validator: { pyxform: "4.5.0", compatibility: "1.0" },
          }),
        ]),
      },
    });

    expect(getApiErrorStatus(parsed)).toBe(503);
    expect(getApiErrorTitle(parsed)).toBe("Survey validation unavailable");
    expect(getApiErrorSummary(parsed)).toBe(
      "[VALIDATOR_UNAVAILABLE] Validator unavailable",
    );
  });

  it("formats legacy strings and structured issue locations", () => {
    expect(
      formatValidationIssues([
        "legacy warning",
        {
          code: "XML_NAME_INVALID",
          layer: "compatibility",
          severity: "error",
          message: "Invalid name",
          field: "name",
        },
      ]),
    ).toEqual([
      "legacy warning",
      "[XML_NAME_INVALID] Invalid name (field name)",
    ]);
  });

  it("parses structured warning headers from binary responses", () => {
    expect(
      parseValidationWarningsHeader(
        JSON.stringify([
          {
            code: "PYXFORM_WARNING",
            layer: "pyxform",
            severity: "warning",
            message: "A non-blocking warning",
          },
        ]),
      ),
    ).toHaveLength(1);
  });
});
