import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import "@testing-library/jest-dom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const statusScript = fs.readFileSync(
  path.resolve(
    __dirname,
    "../../dj-be/survey_designer/apps/questions/static/js/admin/pulldata_status.js",
  ),
  "utf8",
);

function serverResponse(problems) {
  return {
    ok: true,
    json: async () => ({
      files: [
        {
          filename: "growth.csv",
          status: "attached",
          fields: ["calculation"],
        },
      ],
      problems,
      complete: true,
    }),
  };
}

test("live pulldata feedback retires only marked server errors", async () => {
  vi.useFakeTimers();
  document.body.innerHTML = `
    <div class="form-row field-calculation errors">
      <ul class="errorlist">
        <li>RootQuestion 'Q' field 'calculation': Column 'old' does not exist in 'growth.csv'.</li>
        <li>Calculation has an unrelated expression error.</li>
      </ul>
      <textarea id="id_calculation" name="calculation"
        aria-invalid="true" aria-describedby="id_calculation_error id_calculation_helptext">pulldata('growth', 'old', 'id', 1)</textarea>
    </div>
    <div class="form-row field-relevant errors">
      <ul class="errorlist">
        <li>RootQuestion 'Q' field 'relevant': Column 'stale' does not exist in 'growth.csv'.</li>
      </ul>
      <div class="flex-container errors">
        <input id="id_relevant" name="relevant" data-pulldata-server-errors="" aria-invalid="true" />
      </div>
    </div>
    <div class="form-row field-pulldata_files">
      <select id="id_pulldata_files" name="pulldata_files" data-pulldata-status-url="/status">
        <option value="1" selected>growth.csv</option>
      </select>
    </div>
    <div class="form-row field-sub-calculation errors">
      <ul class="errorlist">
        <li>SubQuestion 'S' field 'calculation': Column 'stale' does not exist in 'growth.csv'.</li>
      </ul>
      <div class="flex-container errors">
        <textarea name="sub_questions-0-calculation" aria-invalid="true">pulldata('growth', 'stale', 'id', 1)</textarea>
      </div>
    </div>
    <div class="form-row field-sub-pulldata_files">
      <select name="sub_questions-0-pulldata_files" data-pulldata-status-url="/status">
        <option value="1" selected>growth.csv</option>
      </select>
    </div>
  `;
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      serverResponse([
        "Field 'calculation': Column 'old' does not exist in 'growth.csv'.",
      ]),
    )
    .mockResolvedValueOnce(
      serverResponse([
        "Field 'calculation': Column 'stale' does not exist in 'growth.csv'.",
      ]),
    )
    .mockResolvedValueOnce(
      serverResponse([
        "Field 'calculation': Column 'new' does not exist in 'growth.csv'.",
      ]),
    );
  window.fetch = fetchMock;
  globalThis.fetch = fetchMock;
  document
    .querySelector('[name="calculation"]')
    .setAttribute(
      "data-pulldata-server-errors",
      JSON.stringify([
        "RootQuestion 'Q' field 'calculation': Column 'old' does not exist in 'growth.csv'.",
      ]),
    );
  document
    .querySelector('[name="relevant"]')
    .setAttribute(
      "data-pulldata-server-errors",
      JSON.stringify([
        "RootQuestion 'Q' field 'relevant': Column 'stale' does not exist in 'growth.csv'.",
      ]),
    );
  document
    .querySelector('[name="sub_questions-0-calculation"]')
    .setAttribute(
      "data-pulldata-server-errors",
      JSON.stringify([
        "SubQuestion 'S' field 'calculation': Column 'stale' does not exist in 'growth.csv'.",
      ]),
    );
  window.eval(statusScript);
  document.dispatchEvent(new Event("DOMContentLoaded"));

  const calculation = document.querySelector('[name="calculation"]');
  await vi.waitFor(() =>
    expect(calculation).not.toHaveAttribute("data-pulldata-server-errors"),
  );
  expect(document.querySelectorAll(".errorlist li")).toHaveLength(1);
  expect(document.querySelector(".errorlist").textContent).toContain(
    "unrelated expression error",
  );
  expect(calculation).not.toHaveAttribute("data-pulldata-server-errors");
  expect(calculation).toHaveAttribute("aria-invalid", "true");
  expect(document.querySelector('[name="relevant"]')).not.toHaveAttribute(
    "aria-invalid",
  );
  expect(document.querySelector(".field-relevant")).not.toHaveClass("errors");
  expect(
    document.querySelector(".field-relevant .flex-container"),
  ).not.toHaveClass("errors");
  expect(document.querySelector(".field-calculation")).toHaveClass("errors");
  expect(
    document.querySelector('[name="sub_questions-0-calculation"]'),
  ).not.toHaveAttribute("aria-invalid");
  expect(document.querySelector(".field-sub-calculation")).not.toHaveClass(
    "errors",
  );
  expect(
    document.querySelector(".field-sub-calculation .flex-container"),
  ).not.toHaveClass("errors");
  expect(document.querySelector(".pulldata-status__problem")).toHaveTextContent(
    "old",
  );

  calculation.value = "pulldata('growth', 'new', 'id', 1)";
  calculation.dispatchEvent(new Event("input", { bubbles: true }));
  await vi.advanceTimersByTimeAsync(300);
  await vi.waitFor(() =>
    expect(
      document.querySelector(".pulldata-status__problem"),
    ).toHaveTextContent("new"),
  );

  expect(fetchMock).toHaveBeenCalledTimes(3);

  const subCalculation = document.querySelector(
    '[name="sub_questions-0-calculation"]',
  );
  subCalculation.setAttribute(
    "data-pulldata-server-errors",
    JSON.stringify([
      "SubQuestion 'S' field 'calculation': Column 'new' does not exist in 'growth.csv'.",
    ]),
  );
  const subRow = document.querySelector(".field-sub-calculation");
  subRow.insertAdjacentHTML(
    "afterbegin",
    "<ul class=\"errorlist\"><li>SubQuestion 'S' field 'calculation': Column 'new' does not exist in 'growth.csv'.</li></ul>",
  );
  const subError = subRow.querySelector(".errorlist");
  subError.innerHTML =
    "<li>SubQuestion 'S' field 'calculation': Column 'new' does not exist in 'growth.csv'.</li>";
  fetchMock.mockRejectedValueOnce(new Error("status unavailable"));
  subCalculation.dispatchEvent(new Event("input", { bubbles: true }));
  await vi.advanceTimersByTimeAsync(300);
  expect(subCalculation).toHaveAttribute("data-pulldata-server-errors");
  expect(subError).toContainHTML("Column 'new'");
  vi.useRealTimers();
});
