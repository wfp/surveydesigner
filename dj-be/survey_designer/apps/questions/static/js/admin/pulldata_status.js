// Shows, under each calculation box, which CSV files the question's pulldata()
// calls need and whether they are attached. The server runs the same checks
// as saving; this only shows them while the admin types.
(function () {
  "use strict";

  const EXPRESSION_FIELDS = [
    "calculation",
    "relevant",
    "constraint",
    "required",
    "read_only",
    "default",
    "choice_filter",
  ];
  const FILES_FIELD = "pulldata_files";
  const FILES_SELECTOR = "select[data-pulldata-status-url]";
  const STATUS_TEXT = {
    attached: "attached",
    ambiguous: "ambiguous: select one asset",
    missing: "missing: add it in Pull data files",
    unused: "not used: remove it from Pull data files",
    unchecked: "attached",
  };
  const DELAY_MS = 300;

  const timers = new WeakMap();
  const latestRequest = new WeakMap();

  // "pulldata_files" -> "", "sub_questions-0-pulldata_files" -> "sub_questions-0-"
  function prefixOf(select) {
    return select.name.slice(0, select.name.length - FILES_FIELD.length);
  }

  function input(prefix, field) {
    return document.querySelector(`[name="${prefix}${field}"]`);
  }

  function filesSelectFor(element) {
    const name = (element && element.name) || "";
    const field = EXPRESSION_FIELDS.find(
      (candidate) => name === candidate || name.endsWith(`-${candidate}`),
    );
    if (!field) {
      return null;
    }
    const prefix = name.slice(0, name.length - field.length);
    return document.querySelector(
      `${FILES_SELECTOR}[name="${prefix}${FILES_FIELD}"]`,
    );
  }

  function statusBox(prefix) {
    const calculation = input(prefix, "calculation");
    if (!calculation) {
      return null;
    }
    const anchor = calculation.closest(".flex-container") || calculation;
    let box = anchor.nextElementSibling;
    if (!box || !box.classList.contains("pulldata-status")) {
      box = document.createElement("div");
      // "help" lines the box up with the field, like Django's help text.
      box.className = "help pulldata-status";
      box.setAttribute("aria-live", "polite");
      box.hidden = true;
      anchor.insertAdjacentElement("afterend", box);
    }
    return box;
  }

  function fileItem(file) {
    const item = document.createElement("li");
    item.className = `pulldata-status__file pulldata-status__file--${file.status}`;
    const name = document.createElement("strong");
    name.textContent = file.filename;
    item.append(name, ` ${STATUS_TEXT[file.status] || file.status}`);
    return item;
  }

  function note(text, className) {
    const paragraph = document.createElement("p");
    paragraph.className = className;
    paragraph.textContent = text;
    return paragraph;
  }

  function markedServerErrors(element) {
    if (!element) {
      return [];
    }
    const raw = element.getAttribute("data-pulldata-server-errors");
    if (!raw) {
      return [];
    }
    try {
      const messages = JSON.parse(raw);
      return Array.isArray(messages) ? messages : [];
    } catch (_error) {
      return [];
    }
  }

  function clearMarkedServerErrors(prefix) {
    [...EXPRESSION_FIELDS, FILES_FIELD].forEach((field) => {
      const element = input(prefix, field);
      const messages = markedServerErrors(element);
      if (!element || !messages.length) {
        return;
      }
      const row = element.closest(".form-row");
      if (row) {
        row.querySelectorAll(".errorlist li").forEach((item) => {
          if (messages.includes(item.textContent.trim())) {
            item.remove();
          }
        });
        row.querySelectorAll(".errorlist").forEach((list) => {
          if (!list.querySelector("li")) {
            list.remove();
          }
        });
        if (!row.querySelector(".errorlist li")) {
          row.classList.remove("errors");
          const fieldContainer = element.closest(".flex-container");
          if (
            fieldContainer &&
            !fieldContainer.querySelector(".errorlist li")
          ) {
            fieldContainer.classList.remove("errors");
          }
          element.removeAttribute("aria-invalid");
          const errorId = `${element.id}_error`;
          const describedBy = (element.getAttribute("aria-describedby") || "")
            .split(/\s+/)
            .filter((id) => id && id !== errorId);
          if (describedBy.length) {
            element.setAttribute("aria-describedby", describedBy.join(" "));
          } else {
            element.removeAttribute("aria-describedby");
          }
        }
      }
      element.removeAttribute("data-pulldata-server-errors");
    });
  }

  function render(box, data) {
    box.replaceChildren();
    if (!data.files.length && !data.problems.length && data.complete) {
      box.hidden = true;
      return;
    }
    const label = document.createElement("span");
    label.className = "pulldata-status__label";
    label.textContent = "Pull data:";
    const list = document.createElement("ul");
    list.className = "pulldata-status__files";
    data.files.forEach((file) => list.append(fileItem(file)));
    box.append(label, list);
    data.problems.forEach((problem) =>
      box.append(note(problem, "pulldata-status__problem")),
    );
    if (!data.complete && !data.problems.length) {
      box.append(
        note(
          "Finish the expression to check its pull data files.",
          "pulldata-status__note",
        ),
      );
    }
    box.hidden = false;
  }

  function refresh(select) {
    const prefix = prefixOf(select);
    if (prefix.includes("__prefix__")) {
      return;
    }
    const box = statusBox(prefix);
    if (!box) {
      return;
    }
    const params = new URLSearchParams();
    EXPRESSION_FIELDS.forEach((field) => {
      const element = input(prefix, field);
      if (element && element.value) {
        params.append(field, element.value);
      }
    });
    Array.from(select.selectedOptions).forEach((option) =>
      params.append("files", option.value),
    );

    const request = {};
    latestRequest.set(select, request);
    fetch(`${select.dataset.pulldataStatusUrl}?${params}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        // Ignore answers that arrive after a newer request.
        if (data && latestRequest.get(select) === request) {
          // A failed POST already rendered these exact server errors in the
          // field error list. Once live validation responds successfully, let
          // its current problems be the sole visible pulldata messages.
          clearMarkedServerErrors(prefix);
          render(box, data);
        }
      })
      .catch(() => {});
  }

  function schedule(select) {
    if (!select) {
      return;
    }
    clearTimeout(timers.get(select));
    timers.set(
      select,
      setTimeout(() => refresh(select), DELAY_MS),
    );
  }

  function usesPulldata(select) {
    const prefix = prefixOf(select);
    return (
      select.selectedOptions.length > 0 ||
      EXPRESSION_FIELDS.some((field) => {
        const element = input(prefix, field);
        return element && element.value.includes("pulldata");
      })
    );
  }

  ["input", "tribute-replaced"].forEach((type) =>
    document.addEventListener(type, (event) =>
      schedule(filesSelectFor(event.target)),
    ),
  );
  document.addEventListener("change", (event) => {
    if (event.target.matches && event.target.matches(FILES_SELECTOR)) {
      schedule(event.target);
    }
  });
  // Select2 and the "+" upload popup announce changes through jQuery, which
  // only reaches handlers bound with the same jQuery.
  new Set([window.django && window.django.jQuery, window.jQuery]).forEach(
    ($) => {
      if ($) {
        $(document).on("change", FILES_SELECTOR, function () {
          schedule(this);
        });
      }
    },
  );

  function showInitialStatus() {
    document.querySelectorAll(FILES_SELECTOR).forEach((select) => {
      if (usesPulldata(select)) {
        refresh(select);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", showInitialStatus);
  } else {
    showInitialStatus();
  }
})();
