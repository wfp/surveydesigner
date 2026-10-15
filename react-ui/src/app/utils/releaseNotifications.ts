import { API } from "./index";

export interface ReleaseNotification {
  id: number;
  version: string;
  description: string;
  deployed_at: string;
  state: "unread" | "read" | "cleared";
}

interface ReleaseResponse {
  release: ReleaseNotification | null;
}

export interface ReleaseListResponse {
  results: ReleaseNotification[];
  unread_count: number;
  count?: number;
  next?: string | null;
  previous?: string | null;
}

export const getReleaseNotifications = async (
  signal: AbortSignal,
  mode: "recent" | "history" = "recent",
  page = 1,
) => {
  const response = await API.get<ReleaseListResponse>(
    mode === "recent"
      ? "release-notifications/recent/"
      : "release-notifications/",
    { signal, params: mode === "history" ? { page } : undefined },
  );
  return response.data;
};

export const clearReleaseNotifications = async (
  ids: number[],
  signal: AbortSignal,
) => {
  await API.post(
    "release-notifications/clear/",
    { release_ids: ids },
    {
      signal,
      withXSRFToken: true,
      xsrfCookieName: "csrftoken",
      xsrfHeaderName: "X-CSRFToken",
    },
  );
};

export const getCurrentRelease = async (signal: AbortSignal) => {
  const response = await API.get<ReleaseResponse>(
    "release-notifications/current/",
    { signal },
  );
  return response.data.release;
};

export const updateRelease = async (
  id: number,
  action: "read" | "clear",
  signal: AbortSignal,
) => {
  const response = await API.post<ReleaseResponse>(
    `release-notifications/${id}/${action}/`,
    {},
    {
      signal,
      withXSRFToken: true,
      xsrfCookieName: "csrftoken",
      xsrfHeaderName: "X-CSRFToken",
    },
  );
  return response.data.release;
};
