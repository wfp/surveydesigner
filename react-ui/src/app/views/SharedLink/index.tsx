import React from "react";
import { Module, ModuleBody } from "@wfp/react";
import MainLayout from "../../components/Layout";
import SharedLinkLandingPage from "../../components/SharedLinkLandingPage";

function SharedLink() {
  return (
    <MainLayout
      title="Shared Survey"
      subTitle="Copy a survey from a shared link or export to the desired format"
    >
      <Module>
        <ModuleBody className="shared-link-wrapper">
          <SharedLinkLandingPage />
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}

export default SharedLink;
