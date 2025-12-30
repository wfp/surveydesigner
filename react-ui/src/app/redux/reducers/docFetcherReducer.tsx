import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface DocFetcherState {
  jobId: number | null;
  status: "finished" | "deferred" | "stopped" | "canceled" | "scheduled" | null;
  position: number | null;
}

const initialState: DocFetcherState = {
  jobId: null,
  status: null,
  position: null,
};

export const docFetcherSlice = createSlice({
  name: "docFetcher",
  initialState,
  reducers: {
    setJobId: (state, action: PayloadAction<DocFetcherState>) => ({
      ...state,
      jobId: action.payload.jobId,
      status: action.payload.status,
      position: action.payload.position,
    }),
    clearJobId: (state) => ({
      ...state,
      jobId: null,
      status: null,
      position: null,
    }),
  },
});

export default docFetcherSlice.reducer;

export const docFetcherActions = docFetcherSlice.actions;
