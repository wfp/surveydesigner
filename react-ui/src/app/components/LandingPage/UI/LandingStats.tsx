import React from "react";
import { useTranslation } from "react-i18next";
import styles from "../styles.module.scss";

export function LandingStats() {
  const { t } = useTranslation();

  return (
    <section className={styles.stats}>
      <div className={styles.statsInner}>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{t("landingPage.stat1Value")}</span>
          <span className={styles.statLabel}>{t("landingPage.stat1Label")}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{t("landingPage.stat2Value")}</span>
          <span className={styles.statLabel}>{t("landingPage.stat2Label")}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{t("landingPage.stat3Value")}</span>
          <span className={styles.statLabel}>{t("landingPage.stat3Label")}</span>
        </div>
      </div>
    </section>
  );
}
