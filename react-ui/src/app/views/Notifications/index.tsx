import React, { useEffect, useState } from "react";
import { Button, Loading, Module, ModuleBody } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faArrowRight,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import MainLayout from "../../components/Layout";
import { NotificationFeed } from "../../components/Notifications";
import { useNotifications } from "../../contexts/NotificationsContext";
import {
  fetchNotification,
  fetchRelease,
  formatNotificationDate,
  NotificationDetail,
  ReleaseDetail,
} from "../../utils/notifications";

export default function NotificationsPage() {
  const { t } = useTranslation();
  return (
    <MainLayout title={t("notifications.title")}>
      <Module className="notifications-page">
        <ModuleBody className="notifications-page__body">
          <NotificationFeed />
          <div className="notifications-page__footer">
            <Link to="/releases/latest">
              {t("notifications.latestRelease")}
              <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" />
            </Link>
          </div>
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}

export function NotificationContentPage({
  release = false,
}: {
  release?: boolean;
}) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { account, language, acknowledge, actionError, pendingIds } =
    useNotifications();
  const [content, setContent] = useState<
    NotificationDetail | ReleaseDetail | null
  >(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [readFailed, setReadFailed] = useState(false);

  useEffect(() => {
    if (!account) return undefined;
    const controller = new AbortController();
    let active = true;
    setContent(null);
    setLoading(true);
    setError(null);
    setReadFailed(false);
    const load = async () => {
      try {
        if (id !== "latest" && (!id || !/^\d+$/.test(id) || Number(id) < 1))
          throw new Error("Invalid notification ID");
        if (!release && id === "latest")
          throw new Error("Invalid notification ID");
        const result = release
          ? await fetchRelease(
              id === "latest" ? "latest" : Number(id),
              language,
              controller.signal,
            )
          : await fetchNotification(Number(id), language, controller.signal);
        if (!active) return;
        setContent(result);
        setLoading(false);
        if (!release) {
          // Only deliberate detail navigation acknowledges this exact item.
          const read = await acknowledge(result.id, "read");
          if (active) setReadFailed(!read);
        }
      } catch (reason) {
        if (active && !controller.signal.aborted) {
          setError(reason);
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [id, release, account, language, attempt, acknowledge]);

  const dismiss = async () => {
    if (content && (await acknowledge(content.id, "dismiss")))
      navigate("/notifications");
  };
  const retryRead = async () => {
    if (content) setReadFailed(!(await acknowledge(content.id, "read")));
  };
  const title = release
    ? t("notifications.releaseNotes")
    : t("notifications.title");
  const date =
    content &&
    ("publish_at" in content
      ? content.publish_at
      : content.released_at || content.published_at);
  return (
    <MainLayout title={title}>
      <Module className="notifications-page">
        <ModuleBody className="notification-details">
          <Link className="notification-details__back" to="/notifications">
            <FontAwesomeIcon icon={faArrowLeft} aria-hidden="true" />
            {t("notifications.back")}
          </Link>
          {loading && (
            <p className="notification-feed__status" role="status">
              <Loading small withOverlay={false} />
              {t("notifications.loading")}
            </p>
          )}
          {!!error && (
            <div className="notification-feedback" role="alert">
              <p>{t("notifications.detailError")}</p>
              <Button
                kind="secondary"
                onClick={() => setAttempt((value) => value + 1)}
              >
                {t("notifications.retry")}
              </Button>
            </div>
          )}
          {content && (
            <article
              className="notification-content"
              lang={content.language}
              dir="auto"
            >
              <h2>{content.title}</h2>
              <div className="notification-content__meta">
                {"business_version" in content && (
                  <span>
                    {t("notifications.version", {
                      version: content.business_version,
                    })}
                  </span>
                )}
                {date && (
                  <time dateTime={date}>
                    {formatNotificationDate(date, language)}
                  </time>
                )}
              </div>
              {"abstract" in content && content.abstract && (
                <p className="notification-content__summary">
                  {content.abstract}
                </p>
              )}
              {/* The authenticated consumer API sanitizes body HTML; titles/abstracts remain text. */}
              <div
                className="notification-content__body"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{ __html: content.body }}
              />
              {!release && (
                <>
                  {!!actionError && (
                    <p className="notification-feedback" role="alert">
                      {t("notifications.actionError")}
                    </p>
                  )}
                  <div className="notification-content__actions">
                    {"release_id" in content && content.release_id && (
                      <Link to={`/releases/${content.release_id}`}>
                        {t("notifications.releaseNotes")}
                        <FontAwesomeIcon
                          icon={faArrowRight}
                          aria-hidden="true"
                        />
                      </Link>
                    )}
                    <div className="notification-content__buttons">
                      {readFailed && (
                        <Button
                          small
                          kind="secondary"
                          disabled={pendingIds.includes(content.id)}
                          onClick={() => {
                            retryRead();
                          }}
                        >
                          {t("notifications.retryRead")}
                        </Button>
                      )}
                      <Button
                        kind="secondary"
                        icon={
                          <FontAwesomeIcon icon={faXmark} aria-hidden="true" />
                        }
                        disabled={pendingIds.includes(content.id)}
                        onClick={() => {
                          dismiss();
                        }}
                      >
                        {t("notifications.dismiss")}
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </article>
          )}
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}
