import React, { useEffect, useRef, useState } from "react";
import { Button, Loading, Tag } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBell } from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useNotifications } from "../../contexts/NotificationsContext";
import { formatNotificationDate } from "../../utils/notifications";

export function NotificationFeed({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const {
    notifications,
    loading,
    error,
    actionError,
    pendingIds,
    language,
    refresh,
    acknowledge,
  } = useNotifications();
  return (
    <div aria-busy={loading}>
      {loading && (
        <div role="status">
          <Loading small withOverlay={false} />
          {t("notifications.loading")}
        </div>
      )}
      {!!error && (
        <div role="alert">
          <p>{t("notifications.loadError")}</p>
          <Button
            small
            kind="secondary"
            onClick={() => {
              refresh();
            }}
          >
            {t("notifications.retry")}
          </Button>
        </div>
      )}
      {!!actionError && <p role="alert">{t("notifications.actionError")}</p>}
      {!loading && !error && notifications.length === 0 && (
        <p>{t("notifications.empty")}</p>
      )}
      <ul className="notification-feed">
        {notifications.map((item) => (
          <li
            lang={item.language}
            dir="auto"
            key={item.id}
            className={`notification-feed__item${item.is_read ? "" : " notification-feed__item--unread"}`}
          >
            <Tag type={item.is_read ? "custom" : "info"}>
              {t(item.is_read ? "notifications.read" : "notifications.new")}
            </Tag>
            <Link to={`/notifications/${item.id}`} onClick={onNavigate}>
              {item.title}
            </Link>
            <time dateTime={item.publish_at}>
              {formatNotificationDate(item.publish_at, language)}
            </time>
            {item.abstract && <p>{item.abstract}</p>}
            <Button
              small
              kind="ghost"
              disabled={pendingIds.includes(item.id)}
              aria-label={t("notifications.dismissNamed", {
                title: item.title,
              })}
              onClick={() => {
                acknowledge(item.id, "dismiss");
              }}
            >
              {t("notifications.dismiss")}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function NotificationBell() {
  const { t } = useTranslation();
  const { notifications, refresh } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLLIElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  const unread = notifications.filter((item) => !item.is_read).length;

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const outside = (event: MouseEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
    };
    const focusOutside = (event: FocusEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", escape);
    document.addEventListener("focusin", focusOutside);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("keydown", escape);
      document.removeEventListener("focusin", focusOutside);
    };
  }, [open]);

  return (
    <li className="wfp--main-navigation__item notification-menu" ref={wrapper}>
      <Button
        ref={trigger}
        kind="ghost"
        className="notification-menu__trigger"
        aria-label={
          unread
            ? t("notifications.unreadCount", { count: unread })
            : t("notifications.title")
        }
        aria-expanded={open}
        aria-controls="notification-panel"
        onClick={() => {
          if (!open) refresh();
          setOpen(!open);
        }}
      >
        <FontAwesomeIcon icon={faBell} aria-hidden="true" />
        <span>{t("notifications.title")}</span>
        {unread > 0 && (
          <span className="notification-menu__marker" aria-hidden="true" />
        )}
      </Button>
      {open && (
        <section
          id="notification-panel"
          aria-labelledby="notification-panel-heading"
          className="notification-menu__panel"
        >
          <div className="notification-menu__heading">
            <h2 id="notification-panel-heading">{t("notifications.title")}</h2>
            <Button
              small
              kind="ghost"
              onClick={() => {
                setOpen(false);
                trigger.current?.focus();
              }}
            >
              {t("notifications.close")}
            </Button>
          </div>
          <NotificationFeed onNavigate={() => setOpen(false)} />
          <div className="notification-menu__links">
            <Link to="/notifications" onClick={() => setOpen(false)}>
              {t("notifications.viewAll")}
            </Link>
            <Link to="/releases/latest" onClick={() => setOpen(false)}>
              {t("notifications.latestRelease")}
            </Link>
          </div>
        </section>
      )}
    </li>
  );
}
