import React, { useState } from "react";
import { Button, Callout, InlineLoading } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import MainLayout from "../../components/Layout";
import ReleaseList from "../../components/ReleaseNotifications/ReleaseList";
import { useReleaseNotifications } from "../../components/ReleaseNotifications/useReleaseNotifications";
import { useAppSelector } from "../../redux/store";
import "../../components/ReleaseNotifications/styles.scss";

function NotificationHistory() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const notifications = useReleaseNotifications("history", page);
  return (
    <MainLayout title={t("releaseNotifications.historyTitle")}>
      <section
        className="release-history"
        aria-label={t("releaseNotifications.historyTitle")}
      >
        {notifications.error && (
          <Callout
            kind="error"
            title={t(`releaseNotifications.${notifications.error}Error`)}
            role="alert"
          >
            <Button
              small
              kind="secondary"
              onClick={notifications.retry}
              disabled={notifications.busy}
            >
              {t("releaseNotifications.retry")}
            </Button>
          </Callout>
        )}
        {notifications.loading ? (
          <InlineLoading description={t("releaseNotifications.loading")} />
        ) : (
          <>
            {notifications.releases.length === 0 && !notifications.error && (
              <p>{t("releaseNotifications.empty")}</p>
            )}
            <ReleaseList
              releases={notifications.releases}
              onRead={notifications.read}
              busy={notifications.busy}
            />
            {notifications.total > 20 && (
              <nav
                className="release-history__pages"
                aria-label={t("releaseNotifications.historyTitle")}
              >
                <Button
                  kind="ghost"
                  small
                  icon={<FontAwesomeIcon icon={faChevronLeft} />}
                  aria-label={t("actions.previous")}
                  title={t("actions.previous")}
                  disabled={page === 1 || notifications.busy}
                  onClick={() => setPage(page - 1)}
                />
                <span>
                  {t("releaseNotifications.pages", {
                    page,
                    total: Math.ceil(notifications.total / 20),
                  })}
                </span>
                <Button
                  kind="ghost"
                  small
                  icon={<FontAwesomeIcon icon={faChevronRight} />}
                  aria-label={t("actions.next")}
                  title={t("actions.next")}
                  disabled={
                    page * 20 >= notifications.total || notifications.busy
                  }
                  onClick={() => setPage(page + 1)}
                />
              </nav>
            )}
          </>
        )}
      </section>
    </MainLayout>
  );
}

export default function Notifications() {
  const email = useAppSelector((state) => state.auth.user?.email);
  return <NotificationHistory key={email} />;
}
