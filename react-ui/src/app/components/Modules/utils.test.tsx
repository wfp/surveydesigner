import { beforeEach, describe, expect, it, vi } from "vitest";
import { API } from "../../utils";
import { apiValidation, getValidationSubmoduleId } from "./utils";

vi.mock("../../utils", async () => {
  const actual = await vi.importActual("../../utils");
  return {
    ...(actual as object),
    API: {
      get: vi.fn(),
    },
  };
});

const requestArguments: [
  number[],
  number[],
  number[],
  Record<number, number[]>,
] = [[11], [], [1], { 1: [11, 12] }];

const structuredIssue = {
  code: "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED",
  layer: "composition",
  severity: "error",
  message: "Question B requires Question A.",
  owner: { model: "RootQuestion", id: 21, name: "question_b" },
  submodule: { model: "Submodule", id: 11, name: "nutrition" },
  dependency: { name: "question_a", status: "not_emitted" },
  field: "relevant",
};

describe("Step 2 API validation", () => {
  beforeEach(() => {
    vi.mocked(API.get).mockReset();
  });

  it("preserves structured selected-scope errors", async () => {
    vi.mocked(API.get).mockResolvedValue({
      data: {
        valid: false,
        artifact_hash: "sha256:test",
        errors: [structuredIssue],
        warnings: [],
        validator: { pyxform: "4.5.0", compatibility: "1.0" },
      },
    });

    const result = await apiValidation(...requestArguments);

    expect(result).toEqual({
      ok: false,
      data: [structuredIssue],
    });
    expect(getValidationSubmoduleId(result.data)).toBe(11);
  });

  it("allows a valid selected scope", async () => {
    vi.mocked(API.get).mockResolvedValue({
      data: {
        valid: true,
        artifact_hash: "sha256:test",
        errors: [],
        warnings: [],
        validator: { pyxform: "4.5.0", compatibility: "1.0" },
      },
    });

    await expect(apiValidation(...requestArguments)).resolves.toEqual({
      ok: true,
      data: null,
    });
  });

  it("continues to understand the legacy string-list response", async () => {
    vi.mocked(API.get).mockResolvedValue({ data: ["Legacy validation error"] });

    await expect(apiValidation(...requestArguments)).resolves.toEqual({
      ok: false,
      data: ["Legacy validation error"],
    });
  });

  it("uses a submodule owner when older diagnostics have no scope field", () => {
    expect(
      getValidationSubmoduleId([
        {
          ...structuredIssue,
          submodule: undefined,
          owner: { model: "Submodule", id: 12, name: "food_security" },
        },
      ]),
    ).toBe(12);
  });
});
