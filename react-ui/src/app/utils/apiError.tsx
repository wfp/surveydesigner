import React, { ReactNode } from "react";
import { ApiError } from "../types";
import { ValidationIssue, ValidationResult } from "../types/api";

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

function isValidationIssue(value: unknown): value is ValidationIssue {
  if (!isRecord(value)) return false;

  return (
    typeof value.code === "string" &&
    typeof value.layer === "string" &&
    typeof value.severity === "string" &&
    typeof value.message === "string"
  );
}

function isValidationResult(value: unknown): value is ValidationResult {
  if (!isRecord(value)) return false;

  return (
    typeof value.valid === "boolean" &&
    typeof value.artifact_hash === "string" &&
    Array.isArray(value.errors) &&
    Array.isArray(value.warnings) &&
    isRecord(value.validator)
  );
}

function getStructuredValidationIssues(value: unknown): ValidationIssue[] {
  if (isValidationResult(value)) return value.errors.filter(isValidationIssue);
  if (isRecord(value) && Array.isArray(value.errors)) {
    return value.errors.filter(isValidationIssue);
  }
  return [];
}

function issueLocation(issue: ValidationIssue) {
  const location = [
    issue.sheet && `sheet ${issue.sheet}`,
    issue.column && `column ${issue.column}`,
    issue.row !== undefined && `row ${issue.row}`,
    issue.field &&
      !issue.message.includes(issue.field) &&
      `field ${issue.field}`,
  ].filter(Boolean);

  return location.length ? ` (${location.join(", ")})` : "";
}

export function formatValidationIssues(
  issues: Array<ValidationIssue | string>,
): string[] {
  return issues.map((issue) => {
    if (typeof issue === "string") return issue;
    return `${issue.message}${issueLocation(issue)}`;
  });
}

function collectMessages(value: unknown, messages: string[], prefix?: string) {
  const validationIssues = getStructuredValidationIssues(value);
  if (validationIssues.length) {
    if (isRecord(value)) pushMessage(messages, value.message);
    messages.push(...formatValidationIssues(validationIssues));
    return;
  }

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

  if (typeof Blob !== "undefined" && responseData instanceof Blob) {
    return [fallbackMessage];
  }

  collectMessages(responseData ?? fallbackMessage, messages);

  const uniqueMessages = [...new Set(messages.filter(Boolean))];

  return uniqueMessages.length > 0 ? uniqueMessages : [fallbackMessage];
}

function readBlob(data: Blob): Promise<string> {
  if (typeof data.text === "function") return data.text();

  if (typeof FileReader !== "undefined") {
    return new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => resolve("");
      reader.readAsText(data);
    });
  }

  return Promise.resolve("");
}

async function readErrorPayload(data: unknown): Promise<unknown> {
  let payload = data;
  if (typeof Blob !== "undefined" && data instanceof Blob) {
    payload = await readBlob(data);
  }

  if (typeof payload === "string") {
    try {
      return JSON.parse(payload);
    } catch {
      return payload;
    }
  }

  return payload;
}

/** Decode a JSON error body returned as a Blob while preserving AxiosError shape. */
export async function parseApiError(error: unknown): Promise<ApiError> {
  if (!isRecord(error) || !isRecord(error.response)) {
    return error as unknown as ApiError;
  }

  const response = error.response;
  if (!("data" in response)) return error as unknown as ApiError;

  const payload = await readErrorPayload(response.data);
  if (payload === response.data) return error as unknown as ApiError;

  return {
    ...error,
    response: {
      ...response,
      data: payload,
    },
  } as ApiError;
}

export function getApiErrorStatus(error: unknown): number | undefined {
  const status = (error as any)?.response?.status;
  return typeof status === "number" ? status : undefined;
}

export function getApiErrorTitle(error: unknown, fallback = "Error"): string {
  const status = getApiErrorStatus(error);
  if (isValidationResult((error as any)?.response?.data)) {
    if (status === 400) return "Survey validation failed";
    if (status === 503) return "Survey validation unavailable";
  }
  return fallback;
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

export function parseValidationWarningsHeader(
  value: unknown,
): ValidationIssue[] {
  if (typeof value !== "string") return [];

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter(isValidationIssue) : [];
  } catch {
    return [];
  }
}
