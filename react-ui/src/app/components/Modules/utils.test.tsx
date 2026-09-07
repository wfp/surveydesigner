import { beforeEach, describe, expect, it, vi } from "vitest";
import { API } from "../../utils";
import { apiValidation } from "./utils";

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

describe("Step 2 API validation", () => {
  beforeEach(() => {
    vi.mocked(API.get).mockReset();
  });

  it("formats structured selected-scope errors", async () => {
    vi.mocked(API.get).mockResolvedValue({
      data: {
        valid: false,
        artifact_hash: "sha256:test",
        errors: [
          {
            code: "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED",
            layer: "composition",
            severity: "error",
            message: "Question B requires Question A.",
            field: "relevant",
          },
        ],
        warnings: [],
        validator: { pyxform: "4.5.0", compatibility: "1.0" },
      },
    });

    const result = await apiValidation(...requestArguments);

    expect(result).toEqual({
      ok: false,
      data: ["Question B requires Question A. (field relevant)"],
    });
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
});
