import { Cookies } from "react-cookie";
import { API } from ".";

export interface SurveyNotification {
  id: number;
  release_id: number | null;
  language: string;
  title: string;
  abstract: string;
  publish_at: string;
  expires_at: string | null;
  is_read: boolean;
}

export interface NotificationDetail extends SurveyNotification {
  body: string;
}

export interface ReleaseDetail {
  id: number;
  business_version: string;
  language: string;
  title: string;
  body: string;
  released_at: string | null;
  published_at: string;
}

export type NotificationAction = "read" | "dismiss";
export interface NotificationAcknowledgement {
  id: number;
  state: "read" | "dismissed";
  read_at: string;
  dismissed: boolean;
}

export const fetchNotifications = async (lang: string, signal: AbortSignal) =>
  (
    await API.get<SurveyNotification[]>("/notifications/", {
      params: { lang },
      signal,
    })
  ).data;

export const fetchNotification = async (
  id: number,
  lang: string,
  signal: AbortSignal,
) =>
  (
    await API.get<NotificationDetail>(`/notifications/${id}/`, {
      params: { lang },
      signal,
    })
  ).data;

export const fetchRelease = async (
  id: number | "latest",
  lang: string,
  signal: AbortSignal,
) =>
  (
    await API.get<ReleaseDetail>(`/releases/${id}/`, {
      params: { lang },
      signal,
    })
  ).data;

export const acknowledgeNotification = async (
  id: number,
  action: NotificationAction,
  signal: AbortSignal,
) =>
  (
    await API.post<NotificationAcknowledgement>(
      `/notifications/${id}/acknowledge/`,
      { action },
      { signal, headers: { "X-CSRFToken": new Cookies().get("csrftoken") } },
    )
  ).data;

export function formatNotificationDate(value: string, language: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  try {
    return new Intl.DateTimeFormat(language, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  } catch {
    return new Intl.DateTimeFormat("en", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }
}
