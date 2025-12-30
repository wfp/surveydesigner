import {
  AnyAction,
  configureStore as reduxConfigureStore,
  createAsyncThunk,
  ThunkAction,
} from "@reduxjs/toolkit";
import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";

import rootReducer from "./reducers";

const store = reduxConfigureStore({
  reducer: rootReducer,
  preloadedState: (window as any).initialState || {},
  devTools: (window as any).debug ?? (typeof process !== 'undefined' ? process.env.NODE_ENV === 'development' : false),
  middleware: (defaultMiddleware) =>
    defaultMiddleware().concat(
      ...[
        // Add middlewares here.
      ]
    ),
});

export default store;

export type RootState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  AnyAction
>;

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
export const createAppAsyncThunk = createAsyncThunk.withTypes<{
  state: RootState;
  dispatch: AppDispatch;
  rejectValue: string;
}>();

export const createTestStore = (preloadedState = {}) =>
  reduxConfigureStore({
    reducer: rootReducer,
    preloadedState,
    devTools: (window as any).debug ?? (typeof process !== 'undefined' ? process.env.NODE_ENV === 'development' : false),
    middleware: (defaultMiddleware) =>
      defaultMiddleware().concat(
        // Add middlewares here.
      ),
  });
