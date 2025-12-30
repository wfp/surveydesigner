import React from "react";
import {
  MainNavigationItem,
  SubNavigation,
  SubNavigationContent,
  SubNavigationItem,
  Button,
} from "@wfp/react";
import { langFlags } from "./flags";
import { languages, onChangeLanguage, getUserLanguage } from "../../utils/i18n";

export const languageSelect = () => (
  <MainNavigationItem
    className="wfp--main-navigation__user"
    subNavigation={
      <SubNavigation>
        <SubNavigationContent>
          {languages.map((language) => (
            <SubNavigationItem key={`navbar-languages-${language.value}`}>
              <Button
                kind="ghost"
                small
                icon={
                  langFlags[language.value]
                    ? React.createElement(langFlags[language.value])
                    : undefined
                }
                iconReverse
                onClick={() => onChangeLanguage(language)}
                style={{ fontWeight: "bold" }}
              >
                {language.label}
              </Button>
            </SubNavigationItem>
          ))}
        </SubNavigationContent>
      </SubNavigation>
    }
  >
    <div>{getUserLanguage().toUpperCase()}</div>
  </MainNavigationItem>
);
