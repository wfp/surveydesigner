import React from "react";
import {
  MainNavigationItem,
  SubNavigation,
  SubNavigationContent,
} from "@wfp/react";
import { getUserLanguage } from "../../utils/i18n";
import { LanguageDropdown } from "./LanguageDropdown";

export const languageSelect = () => (
  <MainNavigationItem
    className="wfp--main-navigation__user"
    subNavigation={
      <SubNavigation>
        <SubNavigationContent>
          <LanguageDropdown />
        </SubNavigationContent>
      </SubNavigation>
    }
  >
    <div>{getUserLanguage().toUpperCase()}</div>
  </MainNavigationItem>
);
