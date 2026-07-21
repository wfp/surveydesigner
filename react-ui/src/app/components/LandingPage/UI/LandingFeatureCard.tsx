import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import { useTranslation } from "react-i18next";
import { LandingFeatureItem } from "./featuresData";
import styles from "../styles.module.scss";

type LandingFeatureCardProps = {
  feature: LandingFeatureItem;
  id: string;
  isActive: boolean;
  onSelect: () => void;
};

export function LandingFeatureCard({
  feature,
  id,
  isActive,
  onSelect,
}: LandingFeatureCardProps) {
  const { t } = useTranslation();

  return (
    <button
      id={id}
      type="button"
      className={`${styles.featureItem} ${
        isActive ? styles.featureItemActive : ""
      }`}
      aria-pressed={isActive}
      onClick={onSelect}
    >
      <div className={styles.featureHeader}>
        <span className={styles.featureIcon}>
          <FontAwesomeIcon icon={feature.icon} />
        </span>
        <h3 className={styles.featureTitle}>{t(feature.titleKey)}</h3>
      </div>
      <p className={styles.featureText}>{t(feature.textKey)}</p>
    </button>
  );
}
