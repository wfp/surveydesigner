import React from "react";
import { Button, List, ListItem, Tag } from "@wfp/react";
import { useTranslation } from "react-i18next";
import { ReleaseNotification } from "../../utils/releaseNotifications";

interface ReleaseListProps {
  releases: ReleaseNotification[];
  onRead: (id: number) => void;
  busy: boolean;
  compact?: boolean;
}

export default function ReleaseList({
  releases,
  onRead,
  busy,
  compact = false,
}: ReleaseListProps) {
  const { t, i18n } = useTranslation();
  const dateFormatter = new Intl.DateTimeFormat(
    i18n.resolvedLanguage || i18n.language || "en",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
  return (
    <List
      kind="unstyled"
      className={`release-list${compact ? " release-list--compact" : ""}`}
    >
      {releases.map((release) => (
        <ListItem
          key={release.id}
          className={`release-list__item${release.state === "unread" ? " release-list__item--unread" : ""}`}
        >
          <article
            aria-label={t("releaseNotifications.version", {
              version: release.version,
            })}
          >
            <div className="release-list__heading">
              <h3>
                <Button
                  kind="ghost"
                  className="release-list__title"
                  disabled={busy}
                  onClick={() => {
                    if (release.state === "unread") onRead(release.id);
                  }}
                >
                  {t("releaseNotifications.version", {
                    version: release.version,
                  })}
                </Button>
              </h3>
              <Tag
                type={release.state === "unread" ? "info" : "custom"}
                className={
                  release.state === "unread" ? "" : "release-list__read"
                }
              >
                {t(
                  release.state === "unread"
                    ? "releaseNotifications.new"
                    : "releaseNotifications.read",
                )}
              </Tag>
            </div>
            <time dateTime={release.deployed_at}>
              {dateFormatter.format(new Date(release.deployed_at))}
            </time>
            {release.description && (
              <p className="release-list__description">{release.description}</p>
            )}
          </article>
        </ListItem>
      ))}
    </List>
  );
}
