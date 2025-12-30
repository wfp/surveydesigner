import { RootState } from "../redux/store";
import { UserDetail } from "./api";

declare global {
  export interface Window {
    initialState?: Partial<RootState>;
    debug?: boolean;
    user_data?: UserDetail;
    env?: string;
    static_url?: string;
  }
}

export {};
