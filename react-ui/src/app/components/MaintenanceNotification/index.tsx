import React, { useEffect, useState } from "react";
import { NotificationActionButton, Callout } from "@wfp/react";

import { useAppSelector } from "../../redux/store";

const MAINTENANCE_NOTIFICATION_KEY = "maintenance_notification";
const DISMISS_KEY = `toast_snooze_${MAINTENANCE_NOTIFICATION_KEY}`;

const validKinds = [
  "info",
  "error",
  "success",
  "warning",
  "warning-alt",
] as const;
type NotificationKind = (typeof validKinds)[number];

const MaintenanceNotification = () => {
  const frontendContent = useAppSelector((state) => state.frontendContent.data);
  const [shouldShow, setShouldShow] = useState(false);
  const [notificationData, setNotificationData] = useState<any>(null);

  useEffect(() => {
    const activeNotice = frontendContent?.find(
      (item) =>
        item.key === MAINTENANCE_NOTIFICATION_KEY && item.is_active === true,
    );
    if (!activeNotice) return;

    const snoozedUntil = localStorage.getItem(DISMISS_KEY);
    if (snoozedUntil && new Date(snoozedUntil) > new Date()) return;

    setNotificationData(activeNotice);
    setShouldShow(true);
  }, [frontendContent]);

  const handleSnooze = () => {
    const snoozeUntil = new Date();
    snoozeUntil.setDate(snoozeUntil.getDate() + 1);
    localStorage.setItem(DISMISS_KEY, snoozeUntil.toISOString());
    setShouldShow(false);
  };

  if (!shouldShow || !notificationData) return null;

  const { message, severity = "info" } = notificationData;

  const kind: NotificationKind = validKinds.includes(
    severity as NotificationKind,
  )
    ? (severity as NotificationKind)
    : "info";

  return (
    <div style={{ width: "100%", marginBottom: "1rem" }}>
      <Callout
        kind={kind}
        title="Scheduled Maintenance"
        subtitle={
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1 }}>{message}</div>
            <NotificationActionButton onClick={handleSnooze}>
              Snooze for 1 day
            </NotificationActionButton>
          </div>
        }
        iconDescription="Dismiss"
        statusIconDescription="Maintenance status"
        role="alert"
        onCloseButtonClick={() => setShouldShow(false)}
        hideCloseButton={false}
        lowContrast
        style={{
          marginTop: "2rem",
          marginBottom: "0rem",
          maxWidth: "200rem",
        }}
        isDismissible={true}
      />
    </div>
  );
};

export default MaintenanceNotification;
