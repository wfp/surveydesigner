import React, { ReactNode } from "react";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function humanizeKey(key: string) {
  return key.replace(/_/g, " ");
}

function pushMessage(messages: string[], message: unknown, prefix?: string) {
  if (message === null || message === undefined || message === "") return;

  const text =
    typeof message === "string" || typeof message === "number"
      ? `${message}`
      : JSON.stringify(message);

  messages.push(prefix ? `${humanizeKey(prefix)}: ${text}` : text);
}

function collectMessages(value: unknown, messages: string[], prefix?: string) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectMessages(item, messages, prefix));
    return;
  }

  if (!isRecord(value)) {
    pushMessage(messages, value, prefix);
    return;
  }

  Object.entries(value).forEach(([key, item]) => {
    if (key === "message") {
      pushMessage(messages, item);
      return;
    }

    if (key === "code" || key === "service") {
      pushMessage(messages, item, key);
      return;
    }

    collectMessages(item, messages, prefix ? `${prefix}.${key}` : key);
  });
}

export function getApiErrorMessages(
  error: unknown,
  fallback = "An unknown error occurred.",
) {
  const responseData = (error as any)?.response?.data;
  const fallbackMessage = (error as any)?.message || fallback;
  const messages: string[] = [];

  if (responseData instanceof Blob) {
    return [fallbackMessage];
  }

  collectMessages(responseData ?? fallbackMessage, messages);

  return [...new Set(messages.filter(Boolean))];
}

export function renderApiErrorMessage(
  error: unknown,
  fallback = "An unknown error occurred.",
): ReactNode {
  const messages = getApiErrorMessages(error, fallback);

  if (messages.length <= 1) {
    return messages[0] || fallback;
  }

  const [summary, ...details] = messages;
  return (
    <div className="api-error-message">
      <p>{summary}</p>
      <ul>
        {details.map((detail) => (
          <li key={detail}>{detail}</li>
        ))}
      </ul>
    </div>
  );
}

export function getApiErrorSummary(
  error: unknown,
  fallback = "An unknown error occurred.",
) {
  return getApiErrorMessages(error, fallback).join(" ");
}
