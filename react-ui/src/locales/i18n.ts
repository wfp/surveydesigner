import i18n from "i18next";
import Backend from "i18next-http-backend";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "./en/translations.json";
import es from "./es/translations.json";
import fr from "./fr/translations.json";
import ar from "./ar/translations.json";
import pt from "./pt/translations.json";
import ru from "./ru/translations.json";

export const translationsJson = {
  en: {
    translation: en,
  },
  es: {
    translation: es,
  },
  fr: {
    translation: fr,
  },
  ar: {
    translation: ar,
  },
  pt: {
    translation: pt,
  },
  ru: {
    translation: ru,
  },
};

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: translationsJson,
    interpolation: { escapeValue: false },
    fallbackLng: "en",
    debug: true,
  });

export default i18n;
