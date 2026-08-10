import React, { useEffect, useState, useMemo } from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faTriangleExclamation,
  faCircleQuestion,
} from "@fortawesome/free-solid-svg-icons";

import {
  Checkbox,
  InlineLoading,
  List,
  ListItem,
  Tag,
  TextInput,
  Tooltip,
} from "@wfp/react";

import { useTranslation } from "react-i18next";
import Select, { components, OptionProps } from "react-select";
import { useForm, Controller } from "react-hook-form";
import _ from "lodash";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import {
  OrganizationOption,
  surveyFormActions,
  SurveyFormState,
} from "../../redux/reducers/surveyFormReducer";
import { fetchSurveys } from "../../redux/actions/surveysActions";
import { modulesActions } from "../../redux/reducers/modulesReducer";
import { fetchOrganizations } from "../../redux/actions/organizationsActions";
import { indicatorAreasActions } from "../../redux/reducers/indicatorAreasReducer";
import { indicatorsActions } from "../../redux/reducers/indicatorsReducer";
import { renderTooltipMarkdown } from "../../utils";
import { SurveysProps } from "./Surveys.interface";
import { Organization, SavedSurvey, SurveyCategory } from "../../types/api";
import {
  clearModuleDependentSurveyData,
  haveModuleCriteriaChanged,
} from "./moduleCriteria";

interface CategorySelectOption extends SurveyCategory {
  value: number;
}

function OrganizationCheckboxOption(
  props: OptionProps<OrganizationOption, true>,
) {
  return (
    <components.Option {...props}>
      <div className="survey-organization-option" aria-hidden="true">
        <Checkbox
          id={`organization-option-${props.data.id}`}
          checked={props.isSelected}
          labelText={props.label}
          onChange={() => undefined}
        />
      </div>
    </components.Option>
  );
}

function CategoryOrganizationTags({
  organizations,
}: {
  organizations?: Organization[];
}) {
  if (!organizations?.length) return null;

  const organizationNames = organizations
    .map((organization) => organization.name)
    .join(", ");
  const visibleOrganizations = organizations.slice(0, 2);
  const remainingOrganizationCount =
    organizations.length - visibleOrganizations.length;

  return (
    <Tooltip
      className="survey-category-organizations-tooltip"
      createRefWrapper
      content={`Organizations: ${organizationNames}`}
      dark
      offset={[0, 24]}
      placement="right"
      trigger="hover"
      usePortal
    >
      <span
        className="survey-category-organizations"
        aria-label={`Organizations: ${organizationNames}`}
      >
        {visibleOrganizations.map((organization) => (
          <Tag type="info" key={organization.id}>
            {organization.name}
          </Tag>
        ))}
        {remainingOrganizationCount > 0 && (
          <Tag type="info">+{remainingOrganizationCount}</Tag>
        )}
      </span>
    </Tooltip>
  );
}

function CategoryOptionLabel({ category }: { category: SurveyCategory }) {
  return (
    <div className="survey-category-option">
      <span className="survey-category-option__label">{category.label}</span>
      <CategoryOrganizationTags organizations={category.organizations} />
    </div>
  );
}

function formatCategoryOptionLabel(category: SurveyCategory) {
  return <CategoryOptionLabel category={category} />;
}

function Surveys({
  next,
  frontendContent,
  selectedSurveyToEdit,
  onModuleCriteriaChange,
}: SurveysProps) {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const surveyForm = useAppSelector((state) => state.surveyForm);
  const surveys = useAppSelector((state) => state.surveys);
  const organizations = useAppSelector((state) => state.organizations);

  const [surveyTypes, setSurveyTypes] = useState(
    (surveyForm && surveyForm.category && surveyForm.category.survey_types) ||
      [],
  );

  const [surveyAttributes, setSurveyAttributes] = useState(
    (surveyForm && surveyForm.type && surveyForm.type.attributes) || [],
  );

  // freeze contexts for edit until user changes type/mode
  const [freezeContextUntilChange, setFreezeContextUntilChange] =
    useState(!!selectedSurveyToEdit);

  const organizationOptions: OrganizationOption[] = organizations.data
    ? organizations.data.map((organization) => ({
        id: organization.id,
        value: organization.id,
        label: organization.name,
      }))
    : [];

  function convertSavedObjectToSurveyFormObject(object: any, key: string) {
    return { id: object.id, value: object.id, label: object[key] };
  }

  function convertSurveyToEditToSurveyFormState(
    selectedSurveyToEdit: SavedSurvey | null,
  ): SurveyFormState {
    // Do not default values is no survey is selected
    if (!selectedSurveyToEdit) return {} as SurveyFormState;

    const {
      name,
      survey_category: category,
      survey_type: type,
      survey_mode: mode,
      attributes,
      organizations,
      indicators,
      modules_order,
      submodules,
      submodules_order,
      indicator_areas_order,
      indicators_order,
      languages,
    } = selectedSurveyToEdit;

    return {
      name,
      category: category && {
        id: category.id,
        value: category.id,
        label: category.label,
      },
      type: type && convertSavedObjectToSurveyFormObject(type, "label"),
      mode: mode && convertSavedObjectToSurveyFormObject(mode, "label"),
      attributes: attributes && attributes.map((attribute) => attribute.id),
      organizations:
        organizations &&
        organizations.map((organization) =>
          convertSavedObjectToSurveyFormObject(organization, "name"),
        ),
      indicators: indicators || [],
      modules_order: modules_order || [],
      submodules: submodules || [],
      submodules_order: submodules_order || [],
      indicator_areas_order: indicator_areas_order || [],
      indicators_order: indicators_order || {},
      languages: languages || [],
      sub_questions: [],
    } as unknown as SurveyFormState;
  }

  const isSurveyFormInUse =
    surveyForm.attributes.length > 0 ||
    surveyForm.submodules.length > 0 ||
    surveyForm.sub_questions.length > 0 ||
    (surveyForm.indicators && surveyForm.indicators.length > 0) ||
    surveyForm.category !== null;

  const convertedSavedSurvey: SurveyFormState =
    convertSurveyToEditToSurveyFormState(selectedSurveyToEdit);

  const {
    control,
    handleSubmit,
    setValue,
    getValues,
    watch,
    formState: { errors },
    reset,
  } = useForm<SurveyFormState>({
    defaultValues: {
      ...(isSurveyFormInUse ? surveyForm : convertedSavedSurvey),
    },
  });
  const watchAttributes = watch("attributes", []);
  const watchOrganizations = watch("organizations", []);

  const typeOptions = useMemo(() => {
    const filtered = surveyTypes.filter(
      (t) =>
        t.is_active ||
        (selectedSurveyToEdit && selectedSurveyToEdit.survey_type.id === t.id),
    );

    // Ascending: 1 at top → 10 at bottom
    const sorted = [...filtered].sort(
      (a, b) => (a.order ?? 0) - (b.order ?? 0),
    );

    return sorted.map((t) => ({ ...t, value: t.id }));
  }, [surveyTypes, selectedSurveyToEdit]);

  const categoryOptions = useMemo<CategorySelectOption[]>(
    () =>
      surveys.data?.categories.map((category) => ({
        ...category,
        value: category.id,
      })) || [],
    [surveys.data?.categories],
  );

  // helper to normalize Mode.attributes (IDs or objects)
  function getModeAttrIds(mode: any | null) {
    if (!mode || !mode.attributes) return [];
    return mode.attributes.map((a: any) => (typeof a === "number" ? a : a.id));
  }

  // recompute visible contexts = Type.attributes n Mode.attributes (IDs)
  function recomputeSurveyAttributes(
    selectedType: any | null,
    selectedMode: any | null,
  ) {
    if (!selectedType) {
      setSurveyAttributes([]);
      if (getValues("attributes")?.length) {
        setValue("attributes", []);
      }
      return;
    }
    const typeAttrs = selectedType.attributes || [];
    const modeAttrIds = getModeAttrIds(selectedMode);

    const nextAttributes =
      !selectedMode || modeAttrIds.length === 0
        ? typeAttrs
        : typeAttrs.filter((a: any) => modeAttrIds.includes(a.id));

    setSurveyAttributes(nextAttributes);

    const allowedIds = nextAttributes.map((a: any) => a.id);
    const currentAttrIds = getValues("attributes") || [];
    const filteredAttrIds = currentAttrIds.filter((id: number) =>
      allowedIds.includes(id),
    );

    if (filteredAttrIds.length !== currentAttrIds.length) {
      setValue("attributes", filteredAttrIds);
    }
  }

  useEffect(() => {
    next((proceed) => {
      handleSubmit((data) => {
        const criteriaChanged = haveModuleCriteriaChanged(surveyForm, data);
        const surveyData = criteriaChanged
          ? clearModuleDependentSurveyData(data)
          : data;

        if (criteriaChanged) {
          dispatch(modulesActions.clearModules());
          dispatch(indicatorAreasActions.clearIndicatorAreas());
          dispatch(indicatorsActions.clearIndicators());
          onModuleCriteriaChange();
        }

        dispatch(surveyFormActions.setSurveyData(surveyData));
        proceed?.();
      })();
    });
  }, [next, onModuleCriteriaChange, surveyForm]);

  useEffect(() => {
    if (!organizations.data) {
      dispatch(fetchOrganizations());
    }
  }, []);

  useEffect(() => {
    // Only initialise an edit from the saved snapshot. When returning from a
    // later step, surveyForm already contains the user's in-progress changes.
    if (!isSurveyFormInUse) {
      dispatch(surveyFormActions.setSurveyData(convertedSavedSurvey));
      reset(convertedSavedSurvey);
    }
    // We need to fetch the categories and survey types to populate the dropdowns
    dispatch(fetchSurveys());
  }, [selectedSurveyToEdit]);

  useEffect(() => {
    // Keep the selected category and its dependent fields mounted while a new
    // organization scope is loading. Once the response arrives, replace the
    // options from the fresh union scope and clear only stale selections.
    if (!surveys.data) return;

    const selectedCategoryId = getValues("category")?.id;
    if (!selectedCategoryId) return;

    const selectedCategory = surveys.data.categories.find(
      (category) => category.id === selectedCategoryId,
    );
    const nextSurveyTypes = selectedCategory?.survey_types || [];
    setSurveyTypes(nextSurveyTypes);

    const selectedTypeId = getValues("type")?.id;
    const selectedSurveyType =
      nextSurveyTypes.find((type) => type.id === selectedTypeId) || null;
    if (selectedTypeId && !selectedSurveyType) {
      setValue("type", null);
    }

    const selectedModeId = getValues("mode")?.id;
    const selectedMode =
      surveys.data.modes.find((mode) => mode.id === selectedModeId) || null;
    if (selectedModeId && !selectedMode) {
      setValue("mode", null);
    }

    recomputeSurveyAttributes(selectedSurveyType, selectedMode);
  }, [surveys.data]);

  const updateOrganizationDependencies = (
    nextOrganizations: OrganizationOption[] = getValues("organizations") || [],
    preserveDefinitions = false,
    categoryOverride?: SurveyCategory | null,
  ) => {
    const nextSurveyData = {
      ...getValues(),
      organizations: nextOrganizations,
    };

    if (categoryOverride !== undefined) {
      nextSurveyData.category = categoryOverride;
    }

    if (!preserveDefinitions) {
      nextSurveyData.category = null;
      nextSurveyData.type = undefined;
      nextSurveyData.mode = undefined;
      nextSurveyData.attributes = [];
      setSurveyTypes([]);
      setSurveyAttributes([]);
      setValue("category", null);
      setValue("type", undefined);
      setValue("mode", undefined);
      setValue("attributes", []);
    }

    dispatch(surveyFormActions.setSurveyData(nextSurveyData));
    dispatch(modulesActions.clearModules());
    dispatch(indicatorAreasActions.clearIndicatorAreas());
    dispatch(indicatorsActions.clearIndicators());
    dispatch(fetchSurveys(preserveDefinitions));
  };

  function attributeOnChange(checked: boolean, id: number) {
    const attrs = getValues("attributes");

    if (checked) {
      setValue("attributes", [...attrs, id]);
    } else {
      setValue(
        "attributes",
        attrs.filter((attr) => attr !== id),
      );
    }
  }

  const isLoading = surveys.isLoading || organizations.isLoading;
  const haveData = !!surveys.data && !!organizations.data;
  const haveOrganizations = !!organizations.data;
  const isOrganizationsLoading = organizations.isLoading;

  return (
    <form>
      {isLoading && <InlineLoading description="loading..." />}
      {haveOrganizations && !isOrganizationsLoading && (
        <div className="d-flex survey-definition-layout">
          <div className="flex-column survey-definition-column">
            <div className="wfp--form-item" style={{ marginBottom: "1rem" }}>
              <Controller
                name="name"
                control={control}
                rules={{ required: "This field is required" }}
                render={({ field: { onChange, value } }) => (
                  <TextInput
                    id="id_name_input"
                    value={value}
                    formItemClassName="w-100"
                    placeholder="A clear, memorable title for your survey"
                    invalid={errors.name}
                    invalidText={_.get(errors, "name.message")}
                    labelText={
                      (
                        <span>
                          {t("survey.title")}
                          <span className="required">*</span>
                        </span>
                      ) as unknown as string // TODO: Inorrect type in @wfp/ui
                    }
                    name="survey_name"
                    onChange={(e) => {
                      onChange(e);
                    }}
                  />
                )}
              />
            </div>

            <div className="wfp--form-item" style={{ marginBottom: "1rem" }}>
              {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
              <label htmlFor="id_organization_select" className="wfp--label">
                <div className="d-flex align-items-center">
                  <span style={{ marginRight: "0.5rem" }}>
                    {t("survey.organizations")}
                  </span>
                  <Tooltip
                    createRefWrapper
                    content={renderTooltipMarkdown(
                      frontendContent,
                      "orgTooltip",
                    )}
                    dark
                    placement="top"
                    trigger="hover"
                  >
                    <FontAwesomeIcon
                      className="wfp--btn__icon info-icon"
                      icon={faCircleQuestion}
                    />
                  </Tooltip>
                </div>
              </label>
              <Controller
                name="organizations"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Select
                    className="wfp--react-select-container survey-organization-select"
                    classNamePrefix="wfp--react-select"
                    closeMenuOnSelect={false}
                    components={{ Option: OrganizationCheckboxOption }}
                    id="id_organizations_select"
                    hideSelectedOptions={false}
                    isClearable
                    defaultValue={null}
                    value={value}
                    isMulti
                    options={organizationOptions}
                    onChange={(e) => {
                      onChange(e);
                      updateOrganizationDependencies(e ? [...e] : []);
                    }}
                  />
                )}
              />
            </div>

            {haveData && !!watchOrganizations.length && (
              <>
                <div
                  className="wfp--form-item"
                  style={{ marginBottom: "1rem" }}
                >
                  {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                  <label htmlFor="id_category_select" className="wfp--label">
                    <div className="d-flex align-items-center">
                      <span style={{ marginRight: "0.5rem" }}>
                        {t("survey.category")}
                      </span>
                      <Tooltip
                        createRefWrapper
                        content={renderTooltipMarkdown(
                          frontendContent,
                          "surveyCategoryTooltip",
                        )}
                        dark
                        placement="top"
                        trigger="hover"
                      >
                        <FontAwesomeIcon
                          className="wfp--btn__icon info-icon"
                          icon={faCircleQuestion}
                        />
                      </Tooltip>
                    </div>
                  </label>
                  <Controller
                    name="category"
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        className="wfp--react-select-container"
                        classNamePrefix="wfp--react-select"
                        id="id_category_select"
                        isClearable
                        defaultValue={null}
                        value={
                          categoryOptions.find(
                            (category) => category.id === value?.id,
                          ) || value
                        }
                        options={categoryOptions}
                        formatOptionLabel={formatCategoryOptionLabel}
                        onChange={(e) => {
                          onChange(e);
                          setSurveyTypes((e && e.survey_types) || []);
                          setSurveyAttributes([]);
                          setValue("type", null);
                          setValue("attributes", []);

                          if (e?.organizations?.length) {
                            const selectedOrganizations =
                              getValues("organizations") || [];
                            const selectedOrganizationIds = new Set(
                              selectedOrganizations.map(
                                (organization) => organization.id,
                              ),
                            );
                            const missingOrganizations = e.organizations
                              .filter(
                                (organization) =>
                                  !selectedOrganizationIds.has(organization.id),
                              )
                              .map(
                                (organization) =>
                                  organizationOptions.find(
                                    (option) => option.id === organization.id,
                                  ) || {
                                    id: organization.id,
                                    value: organization.id,
                                    label: organization.name,
                                  },
                              );

                            if (missingOrganizations.length) {
                              const nextOrganizations = [
                                ...selectedOrganizations,
                                ...missingOrganizations,
                              ];
                              setValue("organizations", nextOrganizations, {
                                shouldDirty: true,
                              });
                              updateOrganizationDependencies(
                                nextOrganizations,
                                true,
                                e,
                              );
                            }
                          }
                        }}
                      />
                    )}
                  />
                </div>

                <div style={{ marginBottom: "1rem" }}>
                  <div className="wfp--form-item">
                    {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                    <label htmlFor="id_types_select" className="wfp--label">
                      <div className="d-flex align-items-center">
                        <span style={{ marginRight: "0.5rem" }}>
                          {t("survey.type")}
                        </span>
                        <Tooltip
                          createRefWrapper
                          content={renderTooltipMarkdown(
                            frontendContent,
                            "surveyTypeToolTip",
                          )}
                          dark
                          placement="top"
                          trigger="hover"
                        >
                          <FontAwesomeIcon
                            className="wfp--btn__icon info-icon"
                            icon={faCircleQuestion}
                          />
                        </Tooltip>
                      </div>
                    </label>
                    <Controller
                      name="type"
                      control={control}
                      rules={{
                        required:
                          !!getValues("category") && "This field is required",
                      }}
                      render={({ field: { onChange, value } }) => (
                        <Select
                          className="wfp--react-select-container"
                          classNamePrefix="wfp--react-select"
                          id="id_types_select"
                          isClearable
                          value={value}
                          options={typeOptions}
                          onChange={(e) => {
                            onChange(e);
                            setValue("attributes", []);
                            const currentModeId = getValues("mode")?.id;
                            const currentMode =
                              surveys.data?.modes.find(
                                (mode) => mode.id === currentModeId,
                              ) || null;
                            recomputeSurveyAttributes(e || null, currentMode);
                          }}
                        />
                      )}
                    />
                  </div>
                  {errors.type && (
                    <div className="field-error">
                      <FontAwesomeIcon icon={faTriangleExclamation} />
                      <span>{errors.type.message}</span>
                    </div>
                  )}
                </div>

                <div
                  className="wfp--form-item"
                  style={{ marginBottom: "1rem" }}
                >
                  {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                  <label htmlFor="id_mode_select" className="wfp--label">
                    <div className="d-flex align-items-center">
                      <span style={{ marginRight: "0.5rem" }}>
                        {t("survey.mode")}
                      </span>
                      <Tooltip
                        createRefWrapper
                        content={renderTooltipMarkdown(
                          frontendContent,
                          "surveyModeToolTip",
                        )}
                        dark
                        placement="top"
                        trigger="hover"
                      >
                        <FontAwesomeIcon
                          className="wfp--btn__icon info-icon"
                          icon={faCircleQuestion}
                        />
                      </Tooltip>
                    </div>
                  </label>
                  <Controller
                    name="mode"
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        className="wfp--react-select-container"
                        classNamePrefix="wfp--react-select"
                        id="id_mode_select"
                        isClearable
                        value={value}
                        options={surveys.data?.modes.map((mode) => ({
                          ...mode,
                          value: mode.id,
                        }))}
                        onChange={(e) => {
                          onChange(e);
                          const currentTypeId = getValues("type")?.id;
                          const currentType =
                            surveyTypes.find(
                              (type) => type.id === currentTypeId,
                            ) || null;
                          recomputeSurveyAttributes(currentType, e || null);
                        }}
                      />
                    )}
                  />
                </div>
              </>
            )}
          </div>

          <div className="flex-column survey-definition-column">
            {!_.isEmpty(surveyAttributes) && (
              <div className="wfp--form-item" style={{ marginBottom: "1rem" }}>
                {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                <label className="wfp--label">
                  <div className="d-flex align-items-center">
                    <span style={{ marginRight: "0.5rem" }}>
                      {t("survey.context")}
                    </span>
                    <Tooltip
                      createRefWrapper
                      content={renderTooltipMarkdown(
                        frontendContent,
                        "contextToolTip",
                      )}
                      dark
                      placement="top"
                      trigger="hover"
                    >
                      <FontAwesomeIcon
                        className="wfp--btn__icon info-icon"
                        icon={faCircleQuestion}
                      />
                    </Tooltip>
                  </div>
                </label>
                <List>
                  {surveyAttributes
                    .filter(
                      (attr) =>
                        attr.is_active ||
                        (selectedSurveyToEdit &&
                          selectedSurveyToEdit.attributes?.some(
                            (selectedAttr) => selectedAttr.id === attr.id,
                          )),
                    )
                    .map((attr) => (
                      <ListItem key={attr.id} className="submodule-item">
                        <Controller
                          name="attributes"
                          control={control}
                          render={() => (
                            <Checkbox
                              id={`id-attr-${attr.id}`}
                              labelText={attr.label}
                              value={attr.id}
                              checked={
                                watchAttributes.includes(attr.id) &&
                                surveyAttributes.some(
                                  (item) => item.id === attr.id,
                                )
                              }
                              onChange={({ target: { checked } }) => {
                                attributeOnChange(checked, attr.id);
                              }}
                            />
                          )}
                        />
                      </ListItem>
                    ))}
                </List>
              </div>
            )}
          </div>
        </div>
      )}
    </form>
  );
}

export default Surveys;
