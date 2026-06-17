import { getSavedSelectionsForSubmoduleItems } from "./selection";

describe("Review saved selection helpers", () => {
  it("selects zero-count ancestor branches for saved nested questions", () => {
    const nestedQuestion = {
      id: 14,
      submodule: 1,
      submodule_id: "id-1-estimated-value-monthly",
    };
    const submoduleItems = {
      estimatedValue: {
        id: "id-1-estimated-value",
        sub_questions: [],
        next: {
          monthlyRecall: {
            id: "id-1-estimated-value-monthly",
            sub_questions: [nestedQuestion],
            next: {},
          },
        },
      },
    };

    const result = getSavedSelectionsForSubmoduleItems(
      submoduleItems,
      new Set([nestedQuestion.id]),
    );

    expect(result.selectedQuestions).toEqual([nestedQuestion]);
    expect(new Set(result.selectedIds)).toEqual(
      new Set([
        "id-1-estimated-value",
        "id-1-estimated-value-monthly",
      ]),
    );
  });
});
