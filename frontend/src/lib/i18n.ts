"use client";

import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "@/locales/en.json";
import ru from "@/locales/ru.json";
import zh from "@/locales/zh.json";

if (!i18n.isInitialized) {
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en },
        zh: { translation: zh },
        ru: { translation: ru },
      },
      fallbackLng: "en",
      supportedLngs: ["en", "zh", "ru"],
      interpolation: { escapeValue: false },
    });
}

export default i18n;
