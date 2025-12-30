import React, { Suspense } from "react";
import { createRoot } from "react-dom/client";
import { Loading } from "@wfp/react";
import "./styles/index.scss";
import "./locales/i18n";
import App from "./app";
import { Provider } from "react-redux";
import store from "./app/redux/store";

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(
    <Provider store={store}>
      <Suspense fallback={<Loading withOverlay small={false} />}>
        <App />
      </Suspense>
    </Provider>
  );
}
