import React, { memo } from "react";
import { useTranslation } from "react-i18next";
import { Footer as WFPFooter, Link } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBook, faCircleQuestion, faEnvelope } from "@fortawesome/free-solid-svg-icons";
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
            <p className={styles.footerText}>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla
              facilisi. Vestibulum non orci risus, sit amet tincidunt dui.
            </p>
          </div>
          <div>
            <h3 className={styles.footerHeading}>Product</h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="#about">
                  <FontAwesomeIcon icon={faBook} /> Overview
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">Documentation</Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">Release notes</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className={styles.footerHeading}>Support</h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="#">
                  <FontAwesomeIcon icon={faEnvelope} /> Contact team
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">
                  <FontAwesomeIcon icon={faCircleQuestion} /> Frequently asked
                  questions
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="#">Service status</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className={styles.footerHeading}>World Food Programme</h3>
            <ul className={styles.footerList}>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org" target="_blank">
                  wfp.org
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org/emergencies" target="_blank">
                  Emergencies
                </Link>
              </li>
              <li className={styles.footerListItem}>
                <Link href="https://www.wfp.org/about" target="_blank">
                  About WFP
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
