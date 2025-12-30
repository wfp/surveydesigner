import {
  createSlice,
  PayloadAction,
  SliceCaseReducers,
} from "@reduxjs/toolkit";
import { NotificationKind } from "@wfp/react/src/utils";
import { ReactNode } from "react";

interface NotificationState {
  kind: NotificationKind | null;
  title?: string | null;
  msg?: ReactNode | null;
  show: boolean;
}

type SetNotificationAction = PayloadAction<
  Partial<Pick<NotificationState, "title" | "msg">>
>;

const initialState: NotificationState = {
  kind: null,
  title: null,
  msg: null,
  show: false,
};

export const notificationSlice = createSlice({
  name: "notification",
  initialState,
  reducers: {
    setErrorNotification: (state, action: SetNotificationAction) => ({
      ...state,
      show: true,
      kind: "error",
      title: action.payload.title ?? "Error",
      msg: action.payload.msg,
    }),
    setWarnNotification: (state, action: SetNotificationAction) => ({
      ...state,
      show: true,
      kind: "warning",
      title: action.payload.title ?? "Warning",
      msg: action.payload.msg,
    }),
    setSuccessNotification: (state, action: SetNotificationAction) => ({
      ...state,
      show: true,
      kind: "success",
      title: action.payload.title ?? "Success",
      msg: action.payload.msg,
    }),
    setInfoNotification: (state, action: SetNotificationAction) => ({
      ...state,
      show: true,
      kind: "info",
      title: action.payload.title ?? "",
      msg: action.payload.msg,
    }),
    clearNotification: (state) => ({
      ...state,
      show: false,
      kind: null,
      title: null,
      msg: null,
    }),
  },
});

export default notificationSlice.reducer;

export const notificationsActions = notificationSlice.actions;
