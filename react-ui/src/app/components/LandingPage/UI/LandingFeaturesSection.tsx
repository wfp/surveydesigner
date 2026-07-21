import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import React, { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { LANDING_FEATURES } from "./featuresData";
import { LandingFeatureCard } from "./LandingFeatureCard";
import styles from "../styles.module.scss";

export function LandingFeaturesSection() {
  const { t } = useTranslation();
  const [activeFeatureIndex, setActiveFeatureIndex] = useState(0);
  const activeFeature = LANDING_FEATURES[activeFeatureIndex];
  const nextFeatureIndex = (activeFeatureIndex + 1) % LANDING_FEATURES.length;
  const activeScreenshotSrc = `${window.static_url || ""}img/${activeFeature.image}`;

  const nextFeature = () => {
    setActiveFeatureIndex((index) => (index + 1) % LANDING_FEATURES.length);
  };

  const previousFeature = () => {
    setActiveFeatureIndex(
      (index) =>
        (index - 1 + LANDING_FEATURES.length) % LANDING_FEATURES.length,
    );
  };

  const featureImageAlt = useMemo(
    () => `${t(activeFeature.titleKey)} - Survey Designer Screenshot`,
    [activeFeature.titleKey, t],
  );

  return (
    <div className={styles.mainContent}>
      <section id="about" className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionText}>
            <h2 className={styles.sectionTitle}>
              {t("landingPage.featuresTitle")}
            </h2>
            <p className={styles.sectionIntro}>
              {t("landingPage.featuresIntro")}
            </p>
            <div
              className={styles.featuresGrid}
              role="group"
              aria-label={t("landingPage.featuresTitle")}
            >
              {LANDING_FEATURES.map((feature, index) => (
                <LandingFeatureCard
                  key={feature.titleKey}
                  id={`landing-feature-${index}`}
                  feature={feature}
                  isActive={index === activeFeatureIndex}
                  onSelect={() => setActiveFeatureIndex(index)}
                />
              ))}
            </div>
          </div>
          <div className={styles.sectionVisual} aria-live="polite">
            <button
              type="button"
              className={styles.screenshotWrapper}
              onClick={nextFeature}
              aria-label={`${t("actions.next")}: ${t(
                LANDING_FEATURES[nextFeatureIndex].titleKey,
              )}`}
            >
              <img
                className={styles.screenshot}
                alt={featureImageAlt}
                src={activeScreenshotSrc}
              />
              <div className={styles.screenshotCaption}>
                <h3 className={styles.screenshotTitle}>
                  {t(activeFeature.titleKey)}
                </h3>
                <p className={styles.screenshotText}>
                  {t(activeFeature.textKey)}
                </p>
              </div>
            </button>
            <div className={styles.carouselControls}>
              <button
                type="button"
                className={styles.carouselButton}
                onClick={previousFeature}
                aria-label={t("actions.previous")}
              >
                <FontAwesomeIcon icon={faChevronLeft} />
              </button>
              <div className={styles.carouselDots} aria-hidden="true">
                {LANDING_FEATURES.map((feature, index) => (
                  <span
                    key={feature.titleKey}
                    className={`${styles.carouselDot} ${
                      index === activeFeatureIndex
                        ? styles.carouselDotActive
                        : ""
                    }`}
                  />
                ))}
              </div>
              <button
                type="button"
                className={styles.carouselButton}
                onClick={nextFeature}
                aria-label={t("actions.next")}
              >
                <FontAwesomeIcon icon={faChevronRight} />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
