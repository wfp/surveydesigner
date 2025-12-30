/**
 *
 * @export
 * @enum {string}
 */

import { S } from "vitest/dist/global-60f880c6";

export const ApiTypeEnum = {
  Ona: "ONA",
  Kobo: "KOBO",
} as const;

export type ApiTypeEnum = (typeof ApiTypeEnum)[keyof typeof ApiTypeEnum];

/**
 *
 * @export
 * @interface AuthToken
 */
export interface AuthToken {
  /**
   *
   * @type {string}
   * @memberof AuthToken
   */
  token: string;
}
/**
 *
 * @export
 * @interface AuthTokenRequest
 */
export interface AuthTokenRequest {
  /**
   *
   * @type {string}
   * @memberof AuthTokenRequest
   */
  username: string;
  /**
   *
   * @type {string}
   * @memberof AuthTokenRequest
   */
  password: string;
}
/**
 *
 * @export
 * @interface Choice
 */
export interface Choice {
  /**
   *
   * @type {Array<ChoiceTranslation>}
   * @memberof Choice
   */
  translations: Array<ChoiceTranslation>;
}
/**
 *
 * @export
 * @interface ChoiceGroup
 */
export interface ChoiceGroup {
  /**
   *
   * @type {Array<Choice>}
   * @memberof ChoiceGroup
   */
  choices: Array<Choice>;
}
/**
 *
 * @export
 * @interface ChoiceTranslation
 */
export interface ChoiceTranslation {
  /**
   *
   * @type {LanguageEnum}
   * @memberof ChoiceTranslation
   */
  language: LanguageEnum;
  /**
   *
   * @type {string}
   * @memberof ChoiceTranslation
   */
  language_display: string;
}

/**
 *
 * @export
 * @interface FrontendContent
 */
export interface FrontendContent {
  /**
   *
   * @type {number}
   * @memberof FrontendContent
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof FrontendContent
   */
  message: string;
  /**
   *
   * @type {string}
   * @memberof FrontendContent
   */
  key: string;
}
/**
 *
 * @export
 * @interface GenerateXLSForm
 */
export interface GenerateXLSForm {
  /**
   *
   * @type {string}
   * @memberof GenerateXLSForm
   */
  name: string;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSForm
   */
  submodules: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSForm
   */
  submodules_order: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSForm
   */
  sub_questions: Array<number>;
  /**
   *
   * @type {Array<LanguagesEnum>}
   * @memberof GenerateXLSForm
   */
  languages: Array<LanguagesEnum>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSForm
   */
  indicators?: Array<number>;
}
/**
 *
 * @export
 * @interface GenerateXLSFormRequest
 */
export interface GenerateXLSFormRequest {
  /**
   *
   * @type {string}
   * @memberof GenerateXLSFormRequest
   */
  name: string;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSFormRequest
   */
  submodules: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSFormRequest
   */
  submodules_order: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSFormRequest
   */
  sub_questions: Array<number>;
  /**
   *
   * @type {Array<LanguagesEnum>}
   * @memberof GenerateXLSFormRequest
   */
  languages: Array<LanguagesEnum>;
  /**
   *
   * @type {Array<number>}
   * @memberof GenerateXLSFormRequest
   */
  indicators?: Array<number>;
}
/**
 *
 * @export
 * @interface Indicator
 */
export interface Indicator {
  /**
   *
   * @type {number}
   * @memberof Indicator
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof Indicator
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof Indicator
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof Indicator
   */
  url?: string;
  /**
   *
   * @type {string}
   * @memberof Indicator
   */
  description?: string;
  /**
   *
   * @type {Array<number>}
   * @memberof Indicator
   */
  root_questions: Array<number>;
  /**
   *
   * @type {Array<Submodule>}
   * @memberof Indicator
   */
  submodules: Array<SubmoduleWithQuestions>;
  /**
   *
   * @type {IndicatorArea}
   * @memberof Indicator
   */
  indicator_area: IndicatorArea;
  /**
   * @type {boolean
   * @memberof Indicator}
   */
  is_mandatory: boolean;
}
/**
 *
 * @export
 * @interface IndicatorArea
 */
export interface IndicatorArea {
  /**
   *
   * @type {number}
   * @memberof IndicatorArea
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof IndicatorArea
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof IndicatorArea
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof IndicatorArea
   */
  url?: string;
  /**
   *
   * @type {number}
   * @memberof IndicatorArea
   */
  order?: number;
  /**
   *
   * @type {string}
   * @memberof IndicatorArea
   */
  description?: string;
}
/**
 *
 * @export
 * @enum {string}
 */

export const LanguageEnum = {
  En: "en",
  Fr: "fr",
  Es: "es",
  Ar: "ar",
  ZhCn: "zh-cn",
  Ru: "ru",
} as const;

export type LanguageEnum = (typeof LanguageEnum)[keyof typeof LanguageEnum];

/**
 *
 * @export
 * @enum {string}
 */

export const LanguagesEnum = {
  En: "en",
  Fr: "fr",
  Es: "es",
  Ar: "ar",
  ZhCn: "zh-cn",
  Ru: "ru",
} as const;

export type LanguagesEnum = (typeof LanguagesEnum)[keyof typeof LanguagesEnum];

/**
 *
 * @export
 * @interface Module
 */
export interface Module {
  /**
   *
   * @type {number}
   * @memberof Module
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof Module
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof Module
   */
  description?: string;
  /**
   *
   * @type {Array<Submodule>}
   * @memberof Module
   */
  submodules: Array<Submodule>;
  /**
   *
   * @type {string}
   * @memberof Module
   */
  url?: string;
  /**
   *
   * @type {Array<Organization>}
   * @memberof Module
   */
  organizations: Array<Organization>;
}
/**
 *
 * @export
 * @interface Organization
 */
export interface Organization {
  /**
   *
   * @type {number}
   * @memberof Organization
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof Organization
   */
  name: string;
  /**
   *
   * @type {boolean}
   * @memberof Organization
   */
  is_active?: boolean;
}
/**
 *
 * @export
 * @interface PatchedUserAPIKeyRequest
 */
export interface PatchedUserAPIKeyRequest {
  /**
   *
   * @type {number}
   * @memberof PatchedUserAPIKeyRequest
   */
  site?: number | null;
  /**
   *
   * @type {string}
   * @memberof PatchedUserAPIKeyRequest
   */
  raw_key?: string;
  /**
   *
   * @type {string}
   * @memberof PatchedUserAPIKeyRequest
   */
  name?: string;
}
/**
 *
 * @export
 * @interface RecallPeriod
 */
export interface RecallPeriod {
  /**
   *
   * @type {number}
   * @memberof RecallPeriod
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof RecallPeriod
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof RecallPeriod
   */
  description?: string;
}
/**
 *
 * @export
 * @interface RootQuestion
 */
export interface RootQuestion {
  /**
   *
   * @type {number}
   * @memberof RootQuestion
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof RootQuestion
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof RootQuestion
   */
  label: string;
  /**
   *
   * @type {ChoiceGroup}
   * @memberof RootQuestion
   */
  choices: ChoiceGroup;
  /**
   *
   * @type {Array<SubQuestion>}
   * @memberof RootQuestion
   */
  sub_questions: Array<SubQuestion>;
  /**
   *
   * @type {Array<RootQuestionTranslation>}
   * @memberof RootQuestion
   */
  translations: Array<RootQuestionTranslation>;
}
/**
 *
 * @export
 * @interface RootQuestionTranslation
 */
export interface RootQuestionTranslation {
  /**
   *
   * @type {LanguageEnum}
   * @memberof RootQuestionTranslation
   */
  language: LanguageEnum;
  /**
   *
   * @type {string}
   * @memberof RootQuestionTranslation
   */
  language_display: string;
}

/**
 *
 * @export
 * @interface SubQuestion
 */
export interface SubQuestion {
  /**
   *
   * @type {number}
   * @memberof SubQuestion
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SubQuestion
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof SubQuestion
   */
  label: string;
  /**
   *
   * @type {ChoiceGroup}
   * @memberof SubQuestion
   */
  choices: ChoiceGroup;
  /**
   *
   * @type {Suffix}
   * @memberof SubQuestion
   */
  suffix?: Suffix;
  /**
   *
   * @type {Suffix}
   * @memberof SubQuestion
   */
  suffix_2?: Suffix;
  /**
   *
   * @type {RecallPeriod}
   * @memberof SubQuestion
   */
  recall_period?: RecallPeriod;
  /**
   *
   * @type {Array<{ [key: string]: SubQuestionGroupInnerValue; }>}
   * @memberof SubQuestion
   */
  group: Array<{ [key: string]: SubQuestionGroupInnerValue }>;
  /**
   *
   * @type {Array<SubQuestionTranslation>}
   * @memberof SubQuestion
   */
  translations: Array<SubQuestionTranslation>;
}
/**
 * @type SubQuestionGroupInnerValue
 * @export
 */
export type SubQuestionGroupInnerValue = string;

/**
 *
 * @export
 * @interface SubQuestionTranslation
 */
export interface SubQuestionTranslation {
  /**
   *
   * @type {LanguageEnum}
   * @memberof SubQuestionTranslation
   */
  language: LanguageEnum;
  /**
   *
   * @type {string}
   * @memberof SubQuestionTranslation
   */
  language_display: string;
}

/**
 *
 * @export
 * @interface Submodule
 */
export interface Submodule {
  /**
   *
   * @type {number}
   * @memberof Submodule
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof Submodule
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof Submodule
   */
  description?: string;
  /**
   *
   * @type {boolean}
   * @memberof Submodule
   */
  is_mandatory: boolean;
  /**
   *
   * @type {string}
   * @memberof Submodule
   */
  url?: string;
  /**
   *
   * @type {Array<number>}
   * @memberof Submodule
   */
  root_questions: Array<number>;
  real_item: {
    [key: string]: string | number;
  };
  sub_questions: SubQuestion[];
  submodule: number;
  required?: boolean;
  display: string;
  next: Record<string, Submodule>;
}
/**
 *
 * @export
 * @interface SubmoduleRequiredGroup
 */
export interface SubmoduleRequiredGroup {
  /**
   *
   * @type {string}
   * @memberof SubmoduleRequiredGroup
   */
  suffix?: string;
  /**
   *
   * @type {string}
   * @memberof SubmoduleRequiredGroup
   */
  suffix_2?: string;
  /**
   *
   * @type {string}
   * @memberof SubmoduleRequiredGroup
   */
  recall_period?: string;
}
/**
 *
 * @export
 * @interface SubmoduleWithQuestions
 */
export interface SubmoduleWithQuestions {
  /**
   *
   * @type {number}
   * @memberof SubmoduleWithQuestions
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SubmoduleWithQuestions
   */
  label: string;
  /**
   *
   * @type {Array<RootQuestion>}
   * @memberof SubmoduleWithQuestions
   */
  root_questions: Array<RootQuestion>;
  /**
   *
   * @type {number}
   * @memberof SubmoduleWithQuestions
   */
  module: number;
  /**
   *
   * @type {Array<SubmoduleRequiredGroup>}
   * @memberof SubmoduleWithQuestions
   */
  required_groups: Array<SubmoduleRequiredGroup>;
  /**
   *
   * @type {Array<ChoiceTranslation>}
   * @memberof SubmoduleWithQuestions
   */
  repeat_section_translations: Array<ChoiceTranslation>;
}
/**
 *
 * @export
 * @interface SubmodulesOrderValidationResponse
 */
export interface SubmodulesOrderValidationResponse {
  /**
   *
   * @type {Array<string>}
   * @memberof SubmodulesOrderValidationResponse
   */
  messages: Array<string>;
}
/**
 *
 * @export
 * @interface Suffix
 */
export interface Suffix {
  /**
   *
   * @type {number}
   * @memberof Suffix
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof Suffix
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof Suffix
   */
  description?: string;
}
/**
 *
 * @export
 * @interface SurveyAttribute
 */
export interface SurveyAttribute {
  /**
   *
   * @type {number}
   * @memberof SurveyAttribute
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SurveyAttribute
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof SurveyAttribute
   */
  description?: string;
  is_active?: boolean;
}
/**
 *
 * @export
 * @interface SurveyCategory
 */
export interface SurveyCategory {
  /**
   *
   * @type {number}
   * @memberof SurveyCategory
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SurveyCategory
   */
  label: string;
  /**
   *
   * @type {Array<SurveyTypes>}
   * @memberof SurveyCategory
   */
  survey_types: Array<SurveyTypes>;
  /**
   *
   * @type {string}
   * @memberof SurveyCategory
   */
  description?: string;
}
/**
 *
 * @export
 * @interface SurveyMode
 */
export interface SurveyMode {
  /**
   *
   * @type {number}
   * @memberof SurveyMode
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SurveyMode
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof SurveyMode
   */
  description?: string;
  /**
   * @type {Array<number>}
   * @memberof SurveyMode
   */
  attributes?: Array<number>;
}
/**
 *
 * @export
 * @interface SurveyTypes
 */
export interface SurveyTypes {
  /**
   *
   * @type {number}
   * @memberof SurveyTypes
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SurveyTypes
   */
  label: string;
  /**
   *
   * @type {string}
   * @memberof SurveyTypes
   */
  description?: string;
  /**
   *
   * @type {Array<SurveyAttribute>}
   * @memberof SurveyTypes
   */
  attributes: Array<SurveyAttribute>;
  /**
   *
   * @type {Array<number>}
   * @memberof SurveyTypes
   */
  indicators: Array<number>;
  /**
   *
   * @type {number}
   * @memberof SurveyTypes
   */
  order?: number;
  is_active: boolean;
}
/**
 *
 * @export
 * @interface Surveys
 */
export interface Surveys {
  /**
   *
   * @type {Array<SurveyCategory>}
   * @memberof Surveys
   */
  categories: Array<SurveyCategory>;
  /**
   *
   * @type {Array<SurveyMode>}
   * @memberof Surveys
   */
  modes: Array<SurveyMode>;
}
/**
 *
 * @export
 * @interface UploadXLSFormRequest
 */
export interface UploadXLSFormRequest {
  /**
   *
   * @type {string}
   * @memberof UploadXLSFormRequest
   */
  name: string;
  /**
   *
   * @type {Array<number>}
   * @memberof UploadXLSFormRequest
   */
  submodules: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof UploadXLSFormRequest
   */
  submodules_order: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof UploadXLSFormRequest
   */
  sub_questions: Array<number>;
  /**
   *
   * @type {Array<LanguagesEnum>}
   * @memberof UploadXLSFormRequest
   */
  languages: Array<LanguagesEnum>;
  /**
   *
   * @type {Array<number>}
   * @memberof UploadXLSFormRequest
   */
  indicators?: Array<number>;
  /**
   * UserAPIKey ID
   * @type {number}
   * @memberof UploadXLSFormRequest
   */
  id: number;
  /**
   *
   * @type {number}
   * @memberof UploadXLSFormRequest
   */
  project_id: number | null;
}
/**
 *
 * @export
 * @interface UserAPIKey
 */
export interface UserAPIKey {
  /**
   *
   * @type {number}
   * @memberof UserAPIKey
   */
  id: number;
  /**
   *
   * @type {number}
   * @memberof UserAPIKey
   */
  site?: number | null;
  /**
   *
   * @type {string}
   * @memberof UserAPIKey
   */
  site_url: string;
  /**
   *
   * @type {string}
   * @memberof UserAPIKey
   */
  raw_key: string;
  /**
   *
   * @type {string}
   * @memberof UserAPIKey
   */
  name?: string;
  /**
   *
   * @type {boolean}
   * @memberof UserAPIKey
   */
  is_name_required: boolean;
  /**
   *
   * @type {boolean}
   * @memberof UserAPIKey
   */
  skip_projects: boolean;
}
/**
 *
 * @export
 * @interface UserAPIKeyRead
 */
export interface UserAPIKeyRead {
  /**
   *
   * @type {number}
   * @memberof UserAPIKeyRead
   */
  id: number;
  /**
   *
   * @type {UserAPISite}
   * @memberof UserAPIKeyRead
   */
  site: UserAPISite;
  /**
   *
   * @type {string}
   * @memberof UserAPIKeyRead
   */
  site_url: string;
  /**
   *
   * @type {string}
   * @memberof UserAPIKeyRead
   */
  raw_key: string;
  /**
   *
   * @type {string}
   * @memberof UserAPIKeyRead
   */
  name?: string;
  /**
   *
   * @type {boolean}
   * @memberof UserAPIKeyRead
   */
  is_name_required: boolean;
  /**
   *
   * @type {boolean}
   * @memberof UserAPIKeyRead
   */
  skip_projects: boolean;
}
/**
 *
 * @export
 * @interface UserAPIKeyRequest
 */
export interface UserAPIKeyRequest {
  /**
   *
   * @type {number}
   * @memberof UserAPIKeyRequest
   */
  site?: number | null;
  /**
   *
   * @type {string}
   * @memberof UserAPIKeyRequest
   */
  raw_key: string;
  /**
   *
   * @type {string}
   * @memberof UserAPIKeyRequest
   */
  name?: string;
}
/**
 *
 * @export
 * @interface UserAPISite
 */
export interface UserAPISite {
  /**
   *
   * @type {number}
   * @memberof UserAPISite
   */
  id: number;
  /**
   *
   * @type {ApiTypeEnum}
   * @memberof UserAPISite
   */
  api_type: ApiTypeEnum;
  /**
   *
   * @type {string}
   * @memberof UserAPISite
   */
  name: string;
  /**
   *
   * @type {string}
   * @memberof UserAPISite
   */
  url: string;
}

/**
 *
 * @export
 * @interface UserDetail
 */
export interface UserDetail {
  /**
   *
   * @type {string}
   * @memberof UserDetail
   */
  display_name: string;
  /**
   *
   * @type {string}
   * @memberof UserDetail
   */
  email: string;
  /**
   *
   * @type {boolean}
   * @memberof UserDetail
   */
  can_access_cms: boolean;
  /**
   *
   * @type {Array<UserAPIKey>}
   * @memberof UserDetail
   */
  sites: Array<UserAPIKey>;
  /**
   *
   * @type {boolean}
   * @memberof UserDetail
   */
  read_only_member: boolean;
}
/**
 *
 * @export
 * @interface UserProjectListAPIResponse
 */
export interface UserProjectListAPIResponse {
  /**
   *
   * @type {number}
   * @memberof UserProjectListAPIResponse
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof UserProjectListAPIResponse
   */
  name: string;
}

export interface UploadResponse {
  preview_url?: string;
}

export interface SuffixDict {
  suffix: number;
  suffix_2: number;
  id: number | string;
}
export interface SuffixSerializer {
  [key: number]: SuffixDict[];
}

/**
 *
 * @export
 * @interface SavedSurvey
 */
export interface SavedSurvey {
  /**
   * UUID
   * @type {string | number}
   * @memberof SavedSurvey
   * @example 123e4567-e89b-12d3-a456-426655440000
   */
  uuid: string | number;
  /**
   *
   * @type {number}
   * @memberof SavedSurvey
   */
  id: number;
  /**
   *
   * @type {string}
   * @memberof SavedSurvey
   */
  owner: number;
  /**
   *
   * @type {number}
   * @memberof SavedSurvey
   */
  name: string;
  /**
   *
   * @type {Array<Organization>}
   * @memberof SavedSurvey
   */
  organizations: Array<{ name: string; id: number }>;
  /**
   *
   * @type {SurveyCategory}
   * @memberof SavedSurvey
   */
  survey_category: SurveyCategory;
  /**
   *
   * @type {SurveyTypes}
   * @memberof SavedSurvey
   */
  survey_type: SurveyTypes;
  /**
   *
   * @type {SurveyMode}
   * @memberof SavedSurvey
   */
  survey_mode: SurveyMode;
  /**
   *
   * @type {Array<number>}
   * @memberof SavedSurvey
   */
  indicators: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof SavedSurvey
   */
  submodules: Array<number>;
  /**
   *
   * @type {Array<number>}
   * @memberof SavedSurvey
   */
  subquestion_submodule_mapping: Array<SuffixSerializer>;
  /**
   *
   * @type {Array<number>}
   * @memberof SurveyTypes
   */
  attributes: Array<SurveyAttribute>;
  /**
   *
   * @type {Array<number>}
   * @memberof SavedSurvey
   */
  submodules_order: Array<number>;
  /**
   * @type {Array<{ language: string; language_display: string }>}
   * @memberof SavedSurvey
   */
  languages: Array<{ language: string; language_display: string }>;
}
