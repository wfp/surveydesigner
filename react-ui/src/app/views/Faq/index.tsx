import React, { useEffect } from "react";
import { Module, ModuleBody, Link } from "@wfp/react";
import MainLayout from "../../components/Layout";
import { useAppDispatch, useAppSelector } from "../../redux/store";
import { fetchFrontendContent } from "../../redux/actions/frontendContentActions";
import { renderTextWithImageMarkdown } from "../../utils";

function Faq() {
  const dispatch = useAppDispatch();
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const FAQText = renderTextWithImageMarkdown(frontendContent, "FAQmain");

  useEffect(() => {
    if (!frontendContent) {
      dispatch(fetchFrontendContent());
    }
  }, []);
  return (
    <MainLayout
      title="Help Center"
      subTitle="Learn more about Survey Designer."
    >
      <Module>
        <ModuleBody className="faq-wrapper">{FAQText}</ModuleBody>
      </Module>
    </MainLayout>
  );
}

export default Faq;
