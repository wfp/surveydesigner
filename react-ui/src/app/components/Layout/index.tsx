import React, { memo, useEffect } from "react";
import { Loading, Wrapper } from "@wfp/react";
import { useAppDispatch, useAppSelector } from "../../redux/store";

import Nav from "../Nav";
import Footer from "../Footer";
import Notification from "../Notification";
import { MainLayoutProps } from "./Layout.interface";
import MaintenanceNotification from "../MaintenanceNotification";

function MainLayout(props: MainLayoutProps) {
  const { children, title, subTitle } = props;
  const { isLoading } = useAppSelector((state) => state.app);
  const dispatch = useAppDispatch();
  useEffect(() => {
    document.title = `${title} | WFP Survey Designer`;
  }, [title]);

  return (
    <>
      <Nav />
      <MaintenanceNotification />
      {title && (
        <Wrapper pageWidth="lg" spacing="md">
          <h2>{title}</h2>
          {subTitle && (
            <p
              style={{
                color: "#A9A9A9",
              }}
            >
              {subTitle}
            </p>
          )}
        </Wrapper>
      )}
      <Wrapper background="lighter" pageWidth="lg" spacing="lg">
        {children}
        {isLoading && (
          <Loading
            data-testid="loading-indicator"
            active
            small={false}
            withOverlay
          />
        )}
        <Notification />
      </Wrapper>
      <Footer />
    </>
  );
}

export default memo(MainLayout);
