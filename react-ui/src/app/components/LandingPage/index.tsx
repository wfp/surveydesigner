import React, { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import Footer from "../Footer";
import { LandingPageLocation } from "./LandingPage.interface";
import { LandingFeaturesSection } from "./UI/LandingFeaturesSection";
import { LandingHeader } from "./UI/LandingHeader";
import { LandingHero } from "./UI/LandingHero";
import { LandingStats } from "./UI/LandingStats";
import styles from "./styles.module.scss";

function LandingPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const { from } = (location.state as LandingPageLocation | undefined) || {};
  if (from) {
    localStorage.setItem("from", JSON.stringify(from));
  }

  useEffect(() => {
    document.title = `${t("landingPage.welcome")} | ${t("landingPage.wfp")} ${t(
      "landingPage.title",
    )}`;
  }, [t]);

  return (
    <>
      <div id="landing-page" className={styles.page}>
        <LandingHeader />
        <LandingHero />
        <LandingStats />
        <LandingFeaturesSection />
      </div>
      <Footer />
    </>
  );
}

export default LandingPage;
