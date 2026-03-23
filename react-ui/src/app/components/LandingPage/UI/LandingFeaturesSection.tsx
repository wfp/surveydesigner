import React from "react";
import { useTranslation } from "react-i18next";
import { LANDING_FEATURES } from "./featuresData";
import { LandingFeatureCard } from "./LandingFeatureCard";
import styles from "../styles.module.scss";

export function LandingFeaturesSection() {
  const { t } = useTranslation();
  const screenshotSrc = `${window.static_url || ""}img/home_page_screen.png`;

  return (
    <div className={styles.mainContent}>
      <section id="about" className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionText}>
            <h2 className={styles.sectionTitle}>{t("landingPage.featuresTitle")}</h2>
            <p className={styles.sectionIntro}>{t("landingPage.featuresIntro")}</p>
            <div className={styles.featuresGrid}>
              {LANDING_FEATURES.map((feature) => (
                <LandingFeatureCard key={feature.titleKey} feature={feature} />
              ))}
            </div>
          </div>
          <div className={styles.sectionVisual}>
            <div className={styles.screenshotWrapper}>
              <img
                className={styles.screenshot}
                alt="Survey Designer Screenshot"
                src={screenshotSrc}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
