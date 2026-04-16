/* eslint-disable camelcase */
import { useEffect, useState } from "react";
import { Cookies } from "react-cookie";
import { Controller, useForm } from "react-hook-form";
import Select from "react-select";
import { Button, InlineLoading, ToastNotification, Callout } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileAlt, faSearch } from "@fortawesome/free-solid-svg-icons";

import _ from "lodash";
import { useTranslation } from "react-i18next";

import { useAppDispatch, useAppSelector } from "../../redux/store";

import SubmoduleList from "../SubmoduleList";

import { surveyFormActions } from "../../redux/reducers/surveyFormReducer";
import { surveyWizardUiActions } from "../../redux/reducers/surveyWizardUiReducer";
import { fetchSubmodules } from "../../redux/actions/submodulesActions";
import { submodulesActions } from "../../redux/reducers/submodulesReducer";
import { API } from "../../utils";
import { useModules } from "../../contexts/ModulesContext";
import {
  ChoiceTranslation,
  Indicator,
  LanguageEnum,
  SubQuestion,
  Submodule,
  SubmoduleWithQuestions,
  SuffixSerializer,
} from "../../types/api";
import { ApiError } from "../../types";
import { ReviewProps } from "./Review.interface";
import { getOrderedSubmodules } from "../../utils/generate";

function Review({ next }: ReviewProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const submodulesData = useAppSelector((state) => state.submodules);
  const {
    selectAllReview: selectAll,
    collapseAllReview: collapseAll,
    numberOfQuestionsToBeGenerated,
    selectedSurveyToEdit,
  } = useAppSelector((state) => state.surveyWizardUi);
  const submodules = submodulesData.data;
  const selectedOptions = new Set(submodulesData.selectedOptions);
  const [submodulesMap, setSubmoduleMap] = useState<
    Record<number, Record<string, Submodule>>
  >({});
  const [languages, setLanguages] = useState<ChoiceTranslation[]>([]);
  const [subQuestions, setSubQuestions] = useState(surveyForm.sub_questions);
  const [previewData, setPreviewData] = useState<{
    errors: string[];
    warnings: string[];
  } | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [APIError, setAPIError] = useState<ApiError | null>(null);
  const modulesData = useModules();

  const { data: indicators } = useAppSelector((state) => state.indicators);
  const selectedIndicators =
    useAppSelector((state) =>
      state.surveyForm?.type?.indicators?.filter((indicatorId) =>
        indicators?.find((ind) => ind.id === indicatorId),
      ),
    ) || [];

  const indicatorSubmodules = selectedIndicators.flatMap(
    (indicator) => (indicator as unknown as Indicator).submodules, // NOTE: Incorrect API type
  );
  const relevantSubmodules = [
    ...(submodules || []),
    ...indicatorSubmodules,
  ].reduce(
    (acc, cur) => (acc.find((sub) => sub.id === cur.id) ? acc : [...acc, cur]),
    [] as SubmoduleWithQuestions[],
  );

  const { control, handleSubmit, setValue, getValues } = useForm({
    defaultValues: surveyForm,
  });

  function addToResult(
    result: {
      [key: number]: any;
    },
    listOfSubQuestionSubmodule: (SubQuestion | Submodule)[],
  ) {
    if (listOfSubQuestionSubmodule && listOfSubQuestionSubmodule.length === 0) {
      return result;
    }
    listOfSubQuestionSubmodule.forEach((item) => {
      if (!result[item.id]) {
        result[item.id] = item;
      }
    });
    return result;
  }

  function findSubQuestions(
    submodule: Submodule | SubQuestion,
    suffixList: SuffixSerializer,
    depth: number,
    result: { [key: number]: any },
    parentSuffix?: any,
  ) {
    if (depth === 0 || !submodule) return [];
    const keys = Object.keys(submodule.next);
    let selectedSuffix;
    // check matching recall period
    if (
      parentSuffix &&
      !submodule.real_item.suffix_1_id &&
      !submodule.real_item.suffix_2_id &&
      submodule.real_item.recall_period_id
    ) {
      selectedSuffix = suffixList.find(
        (obj: any) =>
          (obj.suffix_2 === parentSuffix.suffix_2_id ||
            obj.suffix === parentSuffix.suffix_1_id) &&
          obj.recall_period_id === submodule.real_item.recall_period_id,
      );
      // Check matching suffix 2 first
    } else if (parentSuffix && submodule.real_item.suffix_2_id) {
      selectedSuffix = suffixList.find(
        (obj: any) =>
          obj.suffix === parentSuffix.suffix_1_id &&
          obj.suffix_2 === submodule.real_item.suffix_2_id,
      );
      // Check matching suffix 1
    } else if (submodule.real_item.suffix_1_id) {
      selectedSuffix = suffixList.find(
        (obj: any) => obj.suffix === submodule.real_item.suffix_1_id,
      );
    }

    if (!selectedSuffix) return [];
    // If no "next" values, then we can stop here. There are no more subquestions.
    if (keys.length === 0) {
      return submodule.sub_questions;
    }
    result = addToResult(result, [submodule]);
    keys.forEach((key) => {
      const nextSubmodule = submodule.next[key];
      const subQuestions = findSubQuestions(
        nextSubmodule,
        suffixList,
        depth - 1,
        result,
        { ...parentSuffix, ...submodule.real_item },
      );
      if (subQuestions.length > 0) {
        result = addToResult(result, subQuestions);
      }
    });
    return result;
  }

  useEffect(() => {
    if (!submodules) {
      dispatch(fetchSubmodules());
      dispatch(submodulesActions.setSelectedSubmodulesOptions([]));
    }
  }, []);

  useEffect(() => {
    if (submodulesData.data) {
      const [submodulesMapValue, translations] =
        getSubmodulesMap(relevantSubmodules);

      setSubmoduleMap(submodulesMapValue);
      setLanguages([
        { language: "en", language_display: "English" },
        ...translations,
      ]);

      dispatch(
        surveyWizardUiActions.setNumberOfQuestionsToBeGenerated(
          getRootQuestionsCount(submodules),
        ),
      );
      if (!selectedSurveyToEdit) return;
      // This is for preselecting the subquestion check boxes.
      // We need to match the subquestion submodule ID that has been saved to the ones available.
      if (selectedSurveyToEdit.languages) {
        const selectedLanguages = selectedSurveyToEdit.languages;
        setValue("languages", selectedLanguages);
      }

      const selectedQuestions = Object.keys(
        selectedSurveyToEdit.subquestion_submodule_mapping,
      )
        .flatMap((submoduleID) => {
          const foundID = Object.keys(submodulesMapValue).find(
            (key) => submoduleID === key,
          );
          let result: { [key: number]: any } = {};
          if (foundID) {
            const selectedPrefix = submodulesMapValue[parseInt(foundID, 10)];

            const firstKeys = Object.keys(selectedPrefix);
            firstKeys.forEach((key) => {
              const foundSubmodule = selectedPrefix[key];
              const subQuestions = findSubQuestions(
                foundSubmodule,
                selectedSurveyToEdit.subquestion_submodule_mapping[
                  parseInt(submoduleID, 10)
                ],
                3,
                result,
              );
              result = { ...result, ...subQuestions };
            });
          }
          return Object.values(result);
        })
        .filter((submodule) => submodule !== null);
      const selectedIds = [
        ...new Set(
          selectedQuestions.map((item: any) => item.submodule_id || item.id),
        ),
      ];
      const uniqueSelectedQuestions: SubQuestion[] = [];

      selectedQuestions.forEach((item: any) => {
        if (!uniqueSelectedQuestions.find((q: any) => q.id === item.id)) {
          uniqueSelectedQuestions.push(item);
        }
      });
      setSubQuestions([...subQuestions, ...uniqueSelectedQuestions]);
      dispatch(
        submodulesActions.setSelectedSubmodulesOptions([
          ...selectedOptions,
          ...selectedIds,
        ]),
      );
      dispatch(
        surveyWizardUiActions.setNumberOfQuestionsToBeGenerated(
          numberOfQuestionsToBeGenerated + selectedIds.length,
        ),
      );
    }
  }, [submodules]);

  useEffect(() => {
    next((proceed) => {
      handleSubmit((data) => {
        data.submodules = getOrderedSubmodules(surveyForm, modulesData);
        data.submodules_order = modulesData.current.modules_order.flatMap(
          (moduleId) => modulesData.current.submodules_order[moduleId],
        );
        data.sub_questions = subQuestions;
        dispatch(surveyFormActions.setSurveyData(data));
        proceed?.();
      })();
    });
  }, [next]);

  const aggregateSubquestionsFromSubmodule = (array: any) => {
    const result: any = [];
    array.forEach((item: any) => {
      if (item.sub_questions === undefined) {
        result.push(item);
        return;
      }
      result.push(item.sub_questions);
    });
    return result.flatMap((item: any) => item);
  };

  function previewForm() {
    setIsPreviewing(true);

    const timestamp = new Date().getTime().toString();
    const data = {
      name: surveyForm.name || `survey_${timestamp}`,
      submodules: surveyForm.submodules,
      sub_questions: aggregateSubquestionsFromSubmodule(subQuestions).map(
        (item) => item.id,
      ),
      submodules_order: modulesData.current.modules_order.flatMap(
        (moduleId) => modulesData.current.submodules_order[moduleId],
      ),
      languages: getValues("languages").map((item) => item.language),
      indicators: surveyForm.indicators,
    };
    const cookies = new Cookies();
    const csrfToken = cookies.get("csrftoken");
    API.post("/preview/", data, {
      headers: {
        "X-CSRFToken": csrfToken,
      },
    })
      .then((res) => {
        setPreviewData(res.data);
        if (res.data.url) {
          window.open(res.data.enketo_url, "_blank");
        }
        setIsPreviewing(false);
      })
      .catch((err) => {
        setAPIError(err);
        setIsPreviewing(false);
      });
  }

  function wrapMessages(messages: string[]) {
    return (
      <div style={{ marginBottom: "1rem", marginTop: "1rem" }}>
        {messages.map((msg) => (
          // eslint-disable-next-line react/jsx-key
          <div>{msg}</div>
        ))}
      </div>
    );
  }

  function getSubmodulesMap(
    submodules: SubmoduleWithQuestions[],
  ): [Record<number, Record<string, Submodule>>, ChoiceTranslation[]] {
    const submodulesMap: Record<number, Record<number, Submodule>> = {};
    const translations: ChoiceTranslation[] = [];
    const translationLanguageSet = new Set<LanguageEnum>(["en"]);
    const addTranslations = (translations2: ChoiceTranslation[]) =>
      translations2.forEach((translation) => {
        if (!translationLanguageSet.has(translation.language)) {
          translations.push(translation);
          translationLanguageSet.add(translation.language);
        }
      });

    submodules.forEach((submodule) => {
      if (!submodulesMap[submodule.id]) {
        submodulesMap[submodule.id] = {};
      }
      addTranslations(submodule.repeat_section_translations);

      submodule.root_questions
        .flatMap((rootQuestion) => {
          addTranslations(rootQuestion.translations);
          Object.values(rootQuestion.choices?.choices || {}).forEach((choice) =>
            addTranslations(choice.translations),
          );
          return rootQuestion.sub_questions;
        })
        .forEach((subQuestion) => {
          addTranslations(subQuestion.translations);
          Object.values(subQuestion.choices?.choices || {}).forEach((choice) =>
            addTranslations(choice.translations),
          );
          subQuestion.group.forEach((item, index) => {
            let currentPath: string[] = subQuestion.group
              .slice(0, index + 1)
              .map((group) => group.name);

            const lookup = {
              suffix:
                subQuestion.group.find((group) => group.suffix_1_id)?.name ||
                undefined,
              suffix_2:
                subQuestion.group.find((group) => group.suffix_2_id)?.name ||
                undefined,
              recall_period:
                subQuestion.group.find((group) => group.recall_period_id)
                  ?.name || undefined,
            };
            const isRequired = !selectedSurveyToEdit
              ? submodule.required_groups.find(
                  (group) =>
                    group.suffix === lookup.suffix &&
                    group.suffix_2 === lookup.suffix_2 &&
                    group.recall_period === lookup.recall_period,
                )
              : false;

            const extendedSubmoduleId = `id-${submodule.id}-${currentPath.join(
              "-",
            )}`;
            const value = {
              sub_questions: [],
              id: extendedSubmoduleId,
              real_item: item,
              display: item.display,
              submodule: submodule.id,
              required: !!isRequired,
              next: {},
            };

            currentPath = currentPath.reduce(
              (attrs, a) => attrs.concat(a, "next"),
              [] as string[],
            );
            currentPath.pop();

            if (!_.has(submodulesMap[submodule.id], currentPath)) {
              _.set(submodulesMap[submodule.id], currentPath, value);
            }

            if (index + 1 === subQuestion.group.length) {
              currentPath.push("sub_questions");
              const subQuestionList = [
                ..._.get(submodulesMap[submodule.id], currentPath),
                {
                  ...subQuestion,
                  submodule: submodule.id,
                  submodule_id: extendedSubmoduleId,
                },
              ];

              _.set(submodulesMap[submodule.id], currentPath, subQuestionList);
            }
          });
        });
    });
    return [submodulesMap, translations];
  }

  function getRootQuestionsCount(submodules) {
    const rootQuestionsCount =
      submodules?.flatMap(({ root_questions }) => root_questions).length || 0;

    const missedSubQuestionsCount =
      submodules?.flatMap((submodule) =>
        submodule.root_questions.flatMap((root) =>
          root.sub_questions.filter((sub) => sub.suffix?.name === "_oth"),
        ),
      ).length || 0;

    return rootQuestionsCount + missedSubQuestionsCount;
  }

  return (
    <form>
      <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 2 }}>
        {APIError && (
          <Callout
            iconDescription="close"
            kind="error"
            lowContrast
            statusIconDescription=""
            subtitle={
              APIError.response?.data.message
                ? APIError.response.data.message
                : APIError.message
            }
            title="Error"
            // eslint-disable-next-line jsx-a11y/aria-role
            role="api_errors"
            isDismissible={true}
          />
        )}

        {previewData && previewData.errors && previewData.errors.length > 0 && (
          <ToastNotification
            iconDescription="close"
            kind="error"
            lowContrast
            statusIconDescription=""
            subtitle=""
            title="Preview Errors"
            caption=""
            // eslint-disable-next-line jsx-a11y/aria-role
            role="preview_errors"
          >
            {wrapMessages(previewData.errors)}
          </ToastNotification>
        )}

        {previewData &&
          previewData.warnings &&
          previewData.warnings.length > 0 && (
            <Callout
              iconDescription="close"
              kind="warning"
              lowContrast
              statusIconDescription=""
              subtitle=""
              title="Preview Warnings"
              // eslint-disable-next-line jsx-a11y/aria-role
              role="preview_warnings"
              isDismissible={true}
            >
              {wrapMessages(previewData.warnings)}
            </Callout>
          )}
      </div>

      {submodulesData.isLoading && <InlineLoading description="loading..." />}
      {submodules && !submodulesData.isLoading && (
        <div className="d-flex">
          <div className="flex-column">
            <SubmoduleList
              submodules={relevantSubmodules}
              {...{
                collapseAll,
                control,
                getRootQuestionsCount,
                numberOfQuestionsToBeGenerated,
                selectAll,
                selectedOptions,
                setCollapseAll: (val) =>
                  dispatch(surveyWizardUiActions.setCollapseAllReview(val)),
                setNumberOfQuestionsToBeGenerated: (val: number) =>
                  dispatch(
                    surveyWizardUiActions.setNumberOfQuestionsToBeGenerated(
                      val,
                    ),
                  ),
                setSelectAll: (val) =>
                  dispatch(surveyWizardUiActions.setSelectAllReview(val)),
                setSubQuestions,
                submodulesData,
                submodulesMap,
                subQuestions,
              }}
            />
          </div>
          <div className="flex-column">
            <div className="wfp--form-item">
              {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
              <label htmlFor="id_language_select" className="wfp--label">
                {t("review.languages")}
              </label>
              <Controller
                name="languages"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Select
                    className="wfp--react-select-container"
                    classNamePrefix="wfp--react-select"
                    id="id_language_select"
                    isClearable
                    isMulti
                    value={value}
                    getOptionLabel={(opt) => opt.language_display}
                    getOptionValue={(opt) => opt.language}
                    options={languages}
                    onChange={(e) => onChange(e)}
                  />
                )}
              />
            </div>

            <div
              className="d-flex justify-content-center"
              style={{ marginTop: "2rem" }}
            >
              <Button
                kind="primary"
                className="wfp--form-controls__next wfp--btn wfp--btn--primary"
                // eslint-disable-next-line react/jsx-no-bind
                onClick={previewForm}
                disabled={isPreviewing}
                icon={
                  <span
                    style={{ position: "relative", display: "inline-block" }}
                  >
                    <FontAwesomeIcon icon={faFileAlt} size="2x" />
                    <FontAwesomeIcon
                      icon={faSearch}
                      size="1x"
                      style={{
                        position: "absolute",
                        right: 0,
                        bottom: 0,
                        color: "#0a6eb4", // match your theme
                        background: "white",
                        borderRadius: "50%",
                      }}
                    />
                  </span>
                }
                iconReverse
              >
                {t("review.previewSurvey")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}

export default Review;
