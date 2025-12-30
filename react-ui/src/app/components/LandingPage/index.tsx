import React, { useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Link, MainNavigation, MainNavigationItem } from "@wfp/react";
import { useTranslation } from "react-i18next";
import Footer from "../Footer";
import { languageSelect } from "../languageSelect";
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
      <div id="landing-page">
        <div
          className="jumbotron"
          style={{
            backgroundImage: `url(${window.static_url || ""}img/background_1.jpg)`,
          }}
        >
          <div className="text-layer content-block">
            <MainNavigation
              logo={
                <NavLink to="/">
                  {`${t("landingPage.wfp")} | ${t("landingPage.title")}`}
                </NavLink>
              }
              className={styles.navbar}
            >
              <MainNavigationItem>
                <Link
                  href={`${import.meta.env.VITE_APP_API_ENDPOINT}/auth/login/`}
                >
                  {t("actions.login")}
                </Link>
              </MainNavigationItem>
              {languageSelect()}
            </MainNavigation>

            <div className="page-intro">
              <div className="content content-wrapper">
                <h1>
                  {t("landingPage.description")}
                  <Link href="/auth/login/">{t("actions.login")}</Link>{" "}
                  {t("landingPage.learnMore")}
                </h1>
              </div>
            </div>
          </div>
        </div>
        <div className="main-content">
          <div id="product-slideshow">
            <div className="slider">
              <img
                className="responsive"
                alt="Survey Designer Screenshot"
                src={`${window.static_url || ""}img/home_page_screen.png`}
              />
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}

export default LandingPage;
