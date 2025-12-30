import { NotificationKind } from "@wfp/react/src/utils";

export interface Notification {
  kind: NotificationKind;
  title: string;
  subtitle: string;
}
