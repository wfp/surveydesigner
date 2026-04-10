import { describe, expect, it } from "vitest";

import {
  deriveModuleOrderFromSubmodulesOrder,
  getFirstDefinedNestedOrder,
  getFirstDefinedOrder,
  mergeOrderedIds,
} from "./ordering";

describe("Modules ordering helpers", () => {
  it("keeps saved order, removes missing ids, and appends new ids", () => {
    expect(mergeOrderedIds([4, 2, 2, 99], [2, 3, 4, 5])).toEqual([4, 2, 3, 5]);
  });

  it("derives module order from flattened submodule order", () => {
    const modules = [
      {
        id: 10,
        submodules: [{ id: 1 }, { id: 2 }],
      },
      {
        id: 20,
        submodules: [{ id: 3 }, { id: 4 }],
      },
      {
        id: 30,
        submodules: [{ id: 5 }],
      },
    ];

    expect(
      deriveModuleOrderFromSubmodulesOrder([4, 5, 2, 3, 1], modules),
    ).toEqual([20, 30, 10]);
  });

  it("returns the first populated order source", () => {
    expect(getFirstDefinedOrder([], undefined, [3, 2, 1])).toEqual([3, 2, 1]);
  });

  it("reads nested order maps with numeric and string keys", () => {
    expect(
      getFirstDefinedNestedOrder(
        7,
        undefined,
        { 7: [1, 2] },
        { "7": [3, 4] },
      ),
    ).toEqual([1, 2]);

    expect(getFirstDefinedNestedOrder(9, { "9": [8, 7] })).toEqual([8, 7]);
  });
});
