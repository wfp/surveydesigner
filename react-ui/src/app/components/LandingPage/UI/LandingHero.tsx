import { faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Button } from "@wfp/react";
import React from "react";
import { useTranslation } from "react-i18next";
import styles from "../styles.module.scss";

export function LandingHero() {
  const { t } = useTranslation();
  const loginHref = `${import.meta.env.VITE_APP_API_ENDPOINT}/auth/login/`;
  const screenshotSrc = `${window.static_url || ""}img/home_page_screen.png`;

  return (
    <section className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>
            {t("landingPage.heroHeadlineBefore")}
            <span className={styles.heroHighlight}>
              {t("landingPage.heroHeadlineHighlight")}
            </span>
            {t("landingPage.heroHeadlineAfter")}
          </h1>
          <p className={styles.heroSubtitle}>{t("landingPage.heroSubtitle")}</p>
          <Button
            href={loginHref}
            icon={<FontAwesomeIcon icon={faArrowRight} />}
            kind="primary"
          >
            {t("landingPage.heroPrimaryCta")}
          </Button>
        </div>
        <div className={styles.heroVisual}>
          <div className={styles.screenshotCard}>
            <img
              className={styles.screenshot}
              alt="Survey Designer"
              src={screenshotSrc}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
