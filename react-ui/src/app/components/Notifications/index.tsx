import React, { useEffect, useRef, useState } from "react";
import { Button, Loading, Tag } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBell, faXmark } from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useNotifications } from "../../contexts/NotificationsContext";
import { formatNotificationDate } from "../../utils/notifications";

export function NotificationFeed({
  onNavigate,
  compact = false,
}: {
  onNavigate?: () => void;
  compact?: boolean;
}) {
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
    <div className="notification-feed-wrapper" aria-busy={loading}>
      {loading && notifications.length === 0 && (
        <div className="notification-feed__status" role="status">
          <Loading small withOverlay={false} />
          {t("notifications.loading")}
        </div>
      )}
      {!!error && (
        <div className="notification-feedback" role="alert">
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
      {!!actionError && (
        <p className="notification-feedback" role="alert">
          {t("notifications.actionError")}
        </p>
      )}
      {!loading && !error && notifications.length === 0 && (
        <div className="notification-feed__empty">
          <FontAwesomeIcon icon={faBell} aria-hidden="true" />
          <p>{t("notifications.empty")}</p>
        </div>
      )}
      <ul
        className={`notification-feed${compact ? " notification-feed--compact" : ""}`}
      >
        {notifications.map((item) => (
          <li
            lang={item.language}
            dir="auto"
            key={item.id}
            className={`notification-feed__item${item.is_read ? "" : " notification-feed__item--unread"}`}
          >
            <div className="notification-feed__content">
              <div className="notification-feed__meta">
                <Tag
                  className="notification-feed__badge"
                  type={item.is_read ? "custom" : "info"}
                >
                  {t(item.is_read ? "notifications.read" : "notifications.new")}
                </Tag>
                <time dateTime={item.publish_at}>
                  {formatNotificationDate(item.publish_at, language)}
                </time>
              </div>
              <Link
                className="notification-feed__title"
                to={`/notifications/${item.id}`}
                onClick={onNavigate}
              >
                {item.title}
              </Link>
              {item.abstract && (
                <p className="notification-feed__summary">{item.abstract}</p>
              )}
            </div>
            <Button
              small
              kind="ghost"
              className="notification-feed__dismiss"
              icon={<FontAwesomeIcon icon={faXmark} aria-hidden="true" />}
              title={t("notifications.dismiss")}
              disabled={pendingIds.includes(item.id)}
              aria-label={t("notifications.dismissNamed", {
                title: item.title,
              })}
              onClick={() => {
                acknowledge(item.id, "dismiss");
              }}
            >
              {compact ? undefined : t("notifications.dismiss")}
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
  const [panelTop, setPanelTop] = useState(80);
  const wrapper = useRef<HTMLLIElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  const unread = notifications.filter((item) => !item.is_read).length;

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const positionPanel = () => {
      if (trigger.current)
        setPanelTop(trigger.current.getBoundingClientRect().bottom + 8);
    };
    positionPanel();
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
    window.addEventListener("resize", positionPanel);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("keydown", escape);
      document.removeEventListener("focusin", focusOutside);
      window.removeEventListener("resize", positionPanel);
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
        <span className="notification-menu__icon">
          <FontAwesomeIcon icon={faBell} aria-hidden="true" />
          {unread > 0 && (
            <span className="notification-menu__marker" aria-hidden="true" />
          )}
        </span>
        <span>{t("notifications.title")}</span>
      </Button>
      {open && (
        <section
          id="notification-panel"
          aria-labelledby="notification-panel-heading"
          className="notification-menu__panel"
          style={
            {
              "--notification-panel-top": `${panelTop}px`,
            } as React.CSSProperties
          }
        >
          <div className="notification-menu__heading">
            <h2 id="notification-panel-heading">{t("notifications.title")}</h2>
            <Button
              small
              kind="ghost"
              className="notification-menu__close"
              aria-label={t("notifications.close")}
              title={t("notifications.close")}
              icon={<FontAwesomeIcon icon={faXmark} aria-hidden="true" />}
              onClick={() => {
                setOpen(false);
                trigger.current?.focus();
              }}
            />
          </div>
          <div className="notification-menu__body">
            <NotificationFeed compact onNavigate={() => setOpen(false)} />
          </div>
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
