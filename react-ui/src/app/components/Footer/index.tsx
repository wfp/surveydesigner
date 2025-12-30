import React, { memo } from "react";
import { useTranslation } from "react-i18next";
import { Footer as WFPFooter, Link } from "@wfp/react";
import { VERSION } from "../../utils";

function Footer() {
  const { t } = useTranslation();
  const d = new Date();
  const n = d.getFullYear();

  const metaContent = `${n} ©${t("footer.wfp")}`;
  return (
    <div>
      <WFPFooter external metaContent={metaContent} pageWidth="lg">
        <div>
          <ul className="wfp--footer__list">
            <li>
              <Link
                href="http://www1.wfp.org/privacy-policy?_ga=2.46231331.522534847.1576397231-403140018.1571906279"
                target="_blank"
              >
                {t("footer.privacy")}
              </Link>{" "}
              |{" "}
              <Link href="https://cdn.wfp.org/legal/terms/" target="_blank">
                {t("footer.terms")}
              </Link>{" "}
              | <Link href="https://www.wfp.org">{t("footer.link")}</Link>
            </li>
          </ul>
          <small>
            {t("footer.version")}
            {VERSION}
          </small>
        </div>
      </WFPFooter>
    </div>
  );
}

export default memo(Footer);
