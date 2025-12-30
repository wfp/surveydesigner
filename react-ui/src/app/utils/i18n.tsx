import i18n from "i18next";

export const I18nConst = {
  LANGUAGE_LOCAL_STORAGE_KEY: "langCode",
  DEFAULT_LANGUAGE: "en",
};

export const languages = [
  { value: "en", label: "English" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "ar", label: "Arabic" },
  { value: "pt", label: "Portuguese" },
  { value: "ru", label: "Russian" },
];

export const onChangeLanguage = async (option: {
  value: string;
  label: string;
}) => {
  localStorage.setItem(I18nConst.LANGUAGE_LOCAL_STORAGE_KEY, option.value);
  await i18n.changeLanguage(option.value);
};

export const getUserLanguage = () => {
  const lang = localStorage.getItem(I18nConst.LANGUAGE_LOCAL_STORAGE_KEY);
  return lang ? lang : I18nConst.DEFAULT_LANGUAGE;
};
