import { SubQuestion } from "../../types/api";

export interface SavedSubquestionMapping {
  id: number;
}

export interface ReviewSelectionItem {
  id: string | number;
  sub_questions?: ReviewSelectionSubQuestion[];
  next?: Record<string, ReviewSelectionItem>;
}

export interface ReviewSelectionSubQuestion extends Partial<SubQuestion> {
  id: number;
  submodule?: string | number;
  submodule_id?: string | number;
}

export interface SavedSelectionResult {
  selectedQuestions: ReviewSelectionSubQuestion[];
  selectedIds: Array<string | number>;
}

export function getSavedSubquestionIdsBySubmodule(
  savedMappings: Record<string, SavedSubquestionMapping[]> | undefined,
) {
  return Object.entries(savedMappings || {}).reduce<Record<number, Set<number>>>(
    (acc, [submoduleId, mappings]) => {
      acc[parseInt(submoduleId, 10)] = new Set(
        (mappings || []).map((mapping) => mapping.id),
      );
      return acc;
    },
    {},
  );
}

function getSelectionKey(item: ReviewSelectionSubQuestion) {
  return `${item.submodule_id || item.submodule || ""}-${item.id}`;
}

function collectSavedSelectionForItem(
  item: ReviewSelectionItem,
  savedSubquestionIds: Set<number>,
  selectedQuestions: ReviewSelectionSubQuestion[],
  selectedIds: Set<string | number>,
  seenQuestionKeys: Set<string>,
): boolean {
  const itemSubquestions = item.sub_questions || [];
  const matchedSubquestions = itemSubquestions.filter((subQuestion) =>
    savedSubquestionIds.has(subQuestion.id),
  );

  matchedSubquestions.forEach((subQuestion) => {
    const selectionKey = getSelectionKey(subQuestion);
    if (!seenQuestionKeys.has(selectionKey)) {
      selectedQuestions.push(subQuestion);
      seenQuestionKeys.add(selectionKey);
    }
  });

  let hasSavedDescendant = false;
  Object.values(item.next || {}).forEach((child) => {
    if (
      collectSavedSelectionForItem(
        child,
        savedSubquestionIds,
        selectedQuestions,
        selectedIds,
        seenQuestionKeys,
      )
    ) {
      hasSavedDescendant = true;
    }
  });

  const hasAllOwnSubquestionsSaved =
    itemSubquestions.length > 0 &&
    itemSubquestions.every((subQuestion) =>
      savedSubquestionIds.has(subQuestion.id),
    );

  if (hasAllOwnSubquestionsSaved || hasSavedDescendant) {
    selectedIds.add(item.id);
  }

  return matchedSubquestions.length > 0 || hasSavedDescendant;
}

export function getSavedSelectionsForSubmoduleItems(
  submoduleItems: Record<string, ReviewSelectionItem> | undefined,
  savedSubquestionIds: Set<number>,
  seenQuestionKeys = new Set<string>(),
): SavedSelectionResult {
  const selectedQuestions: ReviewSelectionSubQuestion[] = [];
  const selectedIds = new Set<string | number>();

  Object.values(submoduleItems || {}).forEach((item) => {
    collectSavedSelectionForItem(
      item,
      savedSubquestionIds,
      selectedQuestions,
      selectedIds,
      seenQuestionKeys,
    );
  });

  return {
    selectedQuestions,
    selectedIds: [...selectedIds],
  };
}
