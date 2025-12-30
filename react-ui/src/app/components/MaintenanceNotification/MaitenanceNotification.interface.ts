export type NotificationKind =
  | "error"
  | "success"
  | "warning"
  | "warning-alt"
  | "info";

export interface FrontendContentToast {
  id: number;
  key: string;
  message: string;
  is_active?: boolean;
  severity?: NotificationKind;
}
