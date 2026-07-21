import React, { memo } from "react";
import { useTranslation } from "react-i18next";
import { Footer as WFPFooter, Link } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBook,
  faCircleQuestion,
  faEnvelope,
} from "@fortawesome/free-solid-svg-icons";
import { VERSION } from "../../utils";
import styles from "./styles.module.scss";

function Footer() {
  const { t } = useTranslation();
  const d = new Date();
  const n = d.getFullYear();

  return (
    <div className={styles.footer}>
      <WFPFooter pageWidth="full">
        <div className={styles.footerInner}>
          <div>
            <h3 className={styles.footerHeading}>Survey Designer</h3>
            <p className={styles.footerText}>{t("footer.description")}</p>
          </div>
          <div>
            <h3 className={styles.footerHeading}>
              {t("footer.productHeading")}
            </h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="#about">
                  <FontAwesomeIcon icon={faBook} /> {t("footer.overview")}
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">{t("footer.documentation")}</Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">{t("footer.releaseNotes")}</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className={styles.footerHeading}>
              {t("footer.supportHeading")}
            </h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="#">
                  <FontAwesomeIcon icon={faEnvelope} />{" "}
                  {t("footer.contactTeam")}
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">
                  <FontAwesomeIcon icon={faCircleQuestion} /> {t("footer.faq")}
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">{t("footer.serviceStatus")}</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className={styles.footerHeading}>{t("footer.wfpHeading")}</h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org" target="_blank">
                  {t("footer.wfpOrg")}
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org/emergencies" target="_blank">
                  {t("footer.emergencies")}
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org/about" target="_blank">
                  {t("footer.aboutWfp")}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className={styles.footerMeta}>
          <ul className={styles.footerLinks}>
            <li>
              <Link
                href="http://www1.wfp.org/privacy-policy?_ga=2.46231331.522534847.1576397231-403140018.1571906279"
                target="_blank"
              >
                {t("footer.privacy")}
              </Link>
            </li>
            <li>
              <Link href="https://cdn.wfp.org/legal/terms/" target="_blank">
                {t("footer.terms")}
              </Link>
            </li>
            <li>
              <Link href="https://www.wfp.org" target="_blank">
                {t("footer.link")}
              </Link>
            </li>
          </ul>
          <div className={styles.footerVersion}>
            {n} ©{t("footer.wfp")} · {t("footer.version")}
            {VERSION}
          </div>
        </div>
      </WFPFooter>
    </div>
  );
}

export default memo(Footer);
