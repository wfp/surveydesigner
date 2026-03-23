import { Button, Link } from "@wfp/react";
import React from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { LanguageDropdown } from "../../languageSelect/LanguageDropdown";
import styles from "../styles.module.scss";

export function LandingHeader() {
  const { t } = useTranslation();
  const loginHref = `${import.meta.env.VITE_APP_API_ENDPOINT}/auth/login/`;

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <NavLink to="/" className={styles.logo}>
          {t("landingPage.wfp")} | {t("landingPage.title")}
        </NavLink>
        <nav className={styles.navLinks}>
          <Link href="#about" className={styles.navLink}>
            {t("landingPage.navOverview")}
          </Link>
          <Link href="#about" className={styles.navLink}>
            {t("landingPage.navHowItWorks")}
          </Link>
        </nav>
        <div className={styles.headerActions}>
          <LanguageDropdown />
          <Button href={loginHref}>{t("actions.login")}</Button>
        </div>
      </div>
    </header>
  );
}
