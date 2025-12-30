import React from "react";
import { Callout } from "@wfp/react";

import { useAppDispatch, useAppSelector } from "../../redux/store";
import { notificationsActions } from "../../redux/reducers/notificationReducer";

function Notification() {
  const { kind, title, msg, show } = useAppSelector(
    (state) => state.notification,
  );
  const dispatch = useAppDispatch();
  if (show && kind) {
    return (
      <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 1 }}>
        <Callout
          iconDescription="close"
          kind={kind}
          lowContrast
          statusIconDescription=""
          subtitle={msg ?? ""}
          title={title ?? ""}
          onCloseButtonClick={() =>
            dispatch(notificationsActions.clearNotification())
          }
          role="alert"
          isDismissible={true}
        />
      </div>
    );
  }
  // eslint-disable-next-line react/jsx-no-useless-fragment
  return <></>;
}

export default Notification;
