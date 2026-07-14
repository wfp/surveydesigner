import React from "react";
import { Module, ModuleBody } from "@wfp/react";
import { useTranslation } from "react-i18next";
import MainLayout from "../../components/Layout";
import FaqContent from "./FaqContent";

function Faq() {
  const { t } = useTranslation();

  return (
    <MainLayout title={t("helpPage.title")} subTitle={t("helpPage.subtitle")}>
      <Module>
        <ModuleBody className="faq-wrapper">
          <FaqContent />
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}

export default Faq;
