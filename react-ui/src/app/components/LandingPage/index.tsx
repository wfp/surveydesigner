import React, { useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Link } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faClipboardList,
  faGlobe,
  faUsers,
  faShieldAlt,
  faFileLines,
  faDiagramProject,
  faArrowRight,
} from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import Footer from "../Footer";
import { LanguageDropdown } from "../languageSelect/LanguageDropdown";
import { LandingPageLocation } from "./LandingPage.interface";
import styles from "./styles.module.scss";

function LandingPage() {
  const { t } = useTranslation();
  const location = useLocation<LandingPageLocation>();
  const { from } = location.state || {};
  if (from) {
    localStorage.setItem("from", JSON.stringify(from));
  }

  useEffect(() => {
    document.title = `${t("landingPage.welcome")} | ${t("landingPage.wfp")} ${t(
      "landingPage.title",
    )}`;
  }, []);

  return (
    <>
      <div id="landing-page" className={styles.page}>
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
              <Link
                href={`${import.meta.env.VITE_APP_API_ENDPOINT}/auth/login/`}
                className={styles.ctaButton}
              >
                {t("actions.login")}
              </Link>
            </div>
          </div>
        </header>

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
              <p className={styles.heroSubtitle}>
                {t("landingPage.heroSubtitle")}
              </p>
              <Link
                href={`${import.meta.env.VITE_APP_API_ENDPOINT}/auth/login/`}
                className={styles.primaryCta}
              >
                {t("landingPage.heroPrimaryCta")}
                <FontAwesomeIcon icon={faArrowRight} className={styles.ctaArrow} />
              </Link>
            </div>
            <div className={styles.heroVisual}>
              <div className={styles.screenshotCard}>
                <img
                  className={styles.screenshot}
                  alt="Survey Designer"
                  src={`${window.static_url || ""}img/home_page_screen.png`}
                />
              </div>
            </div>
          </div>
        </section>
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
                <div className={styles.featuresGrid}>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faClipboardList} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature1Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature1Text")}
                    </p>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faGlobe} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature2Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature2Text")}
                    </p>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faUsers} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature3Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature3Text")}
                    </p>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faShieldAlt} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature4Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature4Text")}
                    </p>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faDiagramProject} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature5Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature5Text")}
                    </p>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureHeader}>
                      <span className={styles.featureIcon}>
                        <FontAwesomeIcon icon={faFileLines} />
                      </span>
                      <h3 className={styles.featureTitle}>
                        {t("landingPage.feature6Title")}
                      </h3>
                    </div>
                    <p className={styles.featureText}>
                      {t("landingPage.feature6Text")}
                    </p>
                  </div>
                </div>
              </div>
              <div className={styles.sectionVisual}>
                <div className={styles.screenshotWrapper}>
                  <img
                    className={styles.screenshot}
                    alt="Survey Designer Screenshot"
                    src={`${window.static_url || ""}img/home_page_screen.png`}
                  />
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
      <Footer />
    </>
  );
}

export default LandingPage;
