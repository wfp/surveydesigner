/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable react/jsx-no-undef */
import React, { memo } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleQuestion, faSliders } from "@fortawesome/free-solid-svg-icons";
import {
  MainNavigation,
  MainNavigationItem,
  User,
  SubNavigation,
  SubNavigationContent,
  SubNavigationList,
  SubNavigationItem,
} from "@wfp/react";

import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { logout } from "../../redux/actions/authActions";
import { languageSelect } from "../languageSelect";

function Nav() {
  const { t } = useTranslation();
  const auth = useAppSelector((state) => state.auth);
  const dispatch = useAppDispatch();

  const cmsNavigationItem =
    auth.is_logged && auth.user?.can_access_cms ? (
      <MainNavigationItem>
        <a
          href={`${import.meta.env.VITE_APP_API_ENDPOINT}/admin/`}
          target="_blank"
          rel="noopener noreferrer"
          className="d-flex align-items-center"
        >
          <FontAwesomeIcon
            icon={faSliders}
            className="wfp--btn__icon nav-icon"
          />
          <span>
            {auth.is_logged && auth.user?.read_only_member
              ? t("nav.codebook")
              : t("nav.cms")}
          </span>
        </a>
      </MainNavigationItem>
    ) : null;

  const userNavigation = auth.is_logged ? (
    <MainNavigationItem
      className="wfp--main-navigation__user"
      subNavigation={
        <SubNavigation>
          <SubNavigationContent>
            <SubNavigationList>
              <SubNavigationItem>
                <a
                  href="https://ciam.auth.wfp.org/myaccount/personal-info"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("nav.profile")}
                </a>
              </SubNavigationItem>
              <SubNavigationItem>
                <NavLink to="/api-keys">{t("nav.manageApiKeys")}</NavLink>
              </SubNavigationItem>
              <SubNavigationItem>
                <a
                  className="cursor-pointer-on-hover"
                  onClick={() => (window as any).openCookieSettings?.()}
                >
                  {t("nav.cookieSettings", "Cookie settings")}
                </a>
              </SubNavigationItem>
              <SubNavigationItem>
                {/* eslint-disable-next-line jsx-a11y/anchor-is-valid, jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
                <a
                  className="cursor-pointer-on-hover"
                  onClick={() => dispatch(logout())}
                >
                  {t("actions.logout")}
                </a>
              </SubNavigationItem>
            </SubNavigationList>
          </SubNavigationContent>
        </SubNavigation>
      }
    >
      <User alt="User Icon" ellipsis={false} missingImage="avatar" showName>
        {auth.user?.display_name}
      </User>
    </MainNavigationItem>
  ) : (
    <MainNavigationItem>
      <NavLink to="/auth/login/">{t("actions.login")}</NavLink>
    </MainNavigationItem>
  );

  return (
    <MainNavigation
      logo={
        <NavLink to="/">
          {`${t("landingPage.wfp")} |
            ${t("landingPage.title")}`}
        </NavLink>
      }
      mobilePageWidth="full"
      pageWidth="lg"
    >
      {cmsNavigationItem}
      <MainNavigationItem>
        <NavLink to="/help" className="d-flex align-items-center">
          <FontAwesomeIcon
            icon={faCircleQuestion}
            className="wfp--btn__icon nav-icon"
          />
          {t("actions.help")}
        </NavLink>
      </MainNavigationItem>
      {userNavigation}
      {languageSelect()}
    </MainNavigation>
  );
}

export default memo(Nav);
