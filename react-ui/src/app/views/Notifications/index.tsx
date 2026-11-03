import React, { useEffect, useState } from "react";
import { Button, Loading, Module, ModuleBody } from "@wfp/react";
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
      <Module>
        <ModuleBody>
          <NotificationFeed />
          <Link to="/releases/latest">{t("notifications.latestRelease")}</Link>
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
      <Module>
        <ModuleBody>
          <Link to="/notifications">{t("notifications.back")}</Link>
          {loading && (
            <p role="status">
              <Loading small withOverlay={false} />
              {t("notifications.loading")}
            </p>
          )}
          {!!error && (
            <div role="alert">
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
              {"business_version" in content && (
                <p>
                  {t("notifications.version", {
                    version: content.business_version,
                  })}
                </p>
              )}
              {date && (
                <p>
                  <time dateTime={date}>
                    {formatNotificationDate(date, language)}
                  </time>
                </p>
              )}
              {"abstract" in content && content.abstract && (
                <p>{content.abstract}</p>
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
                    <p role="alert">{t("notifications.actionError")}</p>
                  )}
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
                  {"release_id" in content && content.release_id && (
                    <p>
                      <Link to={`/releases/${content.release_id}`}>
                        {t("notifications.releaseNotes")}
                      </Link>
                    </p>
                  )}
                  <Button
                    kind="ghost"
                    disabled={pendingIds.includes(content.id)}
                    onClick={() => {
                      dismiss();
                    }}
                  >
                    {t("notifications.dismiss")}
                  </Button>
                </>
              )}
            </article>
          )}
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}
