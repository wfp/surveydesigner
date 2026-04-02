/*
 * This file is part of SurveyDesigner.
 *
 * SurveyDesigner is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * SurveyDesigner is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with SurveyDesigner. If not, see <https://www.gnu.org/licenses/>.
 */
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
