import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import { useTranslation } from "react-i18next";
import { LandingFeatureItem } from "./featuresData";
import styles from "../styles.module.scss";

type LandingFeatureCardProps = {
  feature: LandingFeatureItem;
};

export function LandingFeatureCard({ feature }: LandingFeatureCardProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.featureItem}>
      <div className={styles.featureHeader}>
        <span className={styles.featureIcon}>
          <FontAwesomeIcon icon={feature.icon} />
        </span>
        <h3 className={styles.featureTitle}>{t(feature.titleKey)}</h3>
      </div>
      <p className={styles.featureText}>{t(feature.textKey)}</p>
    </div>
  );
}
