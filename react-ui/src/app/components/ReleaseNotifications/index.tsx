import React, { useEffect, useRef } from "react";
import { Button, Callout, InlineLoading, Link } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBell, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "../../redux/store";
import { useReleaseNotifications } from "./useReleaseNotifications";
import ReleaseList from "./ReleaseList";
import "./styles.scss";

export function ReleaseNotificationBell() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const notifications = useReleaseNotifications();
  const { releases, unreadCount, loading, busy, error, open } = notifications;
  const root = useRef<HTMLDivElement>(null);
  const bell = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const unread = unreadCount > 0;

  useEffect(() => {
    if (!open) return undefined;
    panel.current?.focus();
    const dismiss = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node))
        notifications.closeDropdown();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        notifications.closeDropdown();
        bell.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const close = () => {
    notifications.closeDropdown();
    bell.current?.focus();
  };

  return (
    <div className="release-notifications" ref={root}>
      <Button
        kind="ghost"
        className="release-notifications__bell"
        ref={bell}
        title={t("releaseNotifications.title")}
        aria-label={t(
          unread ? "releaseNotifications.unread" : "releaseNotifications.title",
        )}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls="release-notifications-panel"
        icon={<FontAwesomeIcon icon={faBell} />}
        onClick={() => {
          if (open) close();
          else notifications.openDropdown();
        }}
      />
      {unread && (
        <span
          className="release-notifications__marker"
          data-testid="release-unread-marker"
        />
      )}
      {open && (
        <div
          className="release-notifications__panel"
          id="release-notifications-panel"
          role="dialog"
          aria-labelledby="release-notifications-title"
          aria-busy={loading || busy}
          tabIndex={-1}
          ref={panel}
          onBlur={(event) => {
            if (
              event.relatedTarget &&
              !root.current?.contains(event.relatedTarget as Node)
            )
              notifications.closeDropdown();
          }}
        >
          <header className="release-notifications__header">
            <h2 id="release-notifications-title">
              {t("releaseNotifications.title")}
            </h2>
            <Button
              kind="ghost"
              small
              className="release-notifications__close"
              onClick={close}
              aria-label={t("actions.close")}
              title={t("actions.close")}
              icon={<FontAwesomeIcon icon={faXmark} />}
            />
          </header>
          {error && (
            <Callout
              kind="error"
              title={t(`releaseNotifications.${error}Error`)}
              role="alert"
            >
              <Button
                small
                kind="secondary"
                onClick={notifications.retry}
                disabled={busy}
              >
                {t("releaseNotifications.retry")}
              </Button>
            </Callout>
          )}
          {loading && (
            <InlineLoading description={t("releaseNotifications.loading")} />
          )}
          {!loading && releases.length === 0 && !error && (
            <p>{t("releaseNotifications.empty")}</p>
          )}
          <ReleaseList
            releases={releases}
            onRead={notifications.read}
            busy={busy}
            compact
          />
          <footer className="release-notifications__footer">
            {releases.length > 0 && (
              <Button
                small
                kind="ghost"
                disabled={busy}
                onClick={notifications.clear}
              >
                {t("releaseNotifications.clear")}
              </Button>
            )}
            <Link
              href="/notifications"
              onClick={(event) => {
                if (
                  event.button === 0 &&
                  !event.ctrlKey &&
                  !event.metaKey &&
                  !event.shiftKey &&
                  !event.altKey
                ) {
                  event.preventDefault();
                  notifications.closeDropdown();
                  navigate("/notifications");
                }
              }}
            >
              {t("releaseNotifications.viewAll")}
            </Link>
          </footer>
        </div>
      )}
    </div>
  );
}

export default function ReleaseNotifications() {
  const { is_logged: loggedIn, user } = useAppSelector((state) => state.auth);
  if (!loggedIn || !user?.email) return null;
  return <ReleaseNotificationBell key={user.email} />;
}
