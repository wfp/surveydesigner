document.addEventListener("DOMContentLoaded", function () {
  const $ = django.jQuery;

  const questionTypeSelect = $("#id_type");

  function toggleChoicesWrapper(questionType) {
    const $choices = $("#id_choices");
    const $choicesWrapper = $choices.closest(".form-row");
    const $choicesLabel = $choicesWrapper.find("label");
    if (!$choicesLabel.text().includes("*")) {
      $choicesLabel.text($choicesLabel.text() + " *");
    }

    const $choicesFile = $("#id_choices_file");
    const $choicesFileWrapper = $choicesFile.closest(".form-row");
    const $choicesFileLabel = $choicesFileWrapper.find("label");
    if (!$choicesFileLabel.text().includes("*")) {
      $choicesFileLabel.text($choicesFileLabel.text() + " *");
    }

    function makeLabelBold($label) {
      if ($label.length && $label.find("strong").length === 0) {
        $label.wrapInner("<strong></strong>");
      }
    }

    function makeLabelNotBold($label) {
      if ($label.length) {
        $label.find("strong").each(function () {
          $(this).replaceWith($(this).contents());
        });
      }
    }

    if (
      ["select_one_from_file", "select_multiple_from_file"].indexOf(
        questionType
      ) !== -1
    ) {
      $choicesFileWrapper.show();
      $choicesFile.prop("required", true);
      makeLabelBold($choicesFileLabel);
      $("#id_choices option:selected").prop("selected", false);
      $choicesWrapper.hide();
      $choices.prop("required", false);
      makeLabelNotBold($choicesLabel);
    } else {
      $choicesFile.val("");
      $choicesFileWrapper.hide();
      $choicesFile.prop("required", false);
      makeLabelNotBold($choicesFileLabel);

      if (["select_one", "select_multiple"].indexOf(questionType) !== -1) {
        $choicesWrapper.show();
        $choices.prop("required", true);
        makeLabelBold($choicesLabel);
      } else {
        $("#id_choices option:selected").prop("selected", false);
        $choicesWrapper.hide();
        $choices.prop("required", false);
        makeLabelNotBold($choicesLabel);
      }
    }
  }

  toggleChoicesWrapper(questionTypeSelect.val());

  questionTypeSelect.change(function () {
    toggleChoicesWrapper(this.value);
  });

  const prefix = "id_sub_questions-";
  const suffix = "-suffix";
  const suffix2 = "-suffix_2";

  $(document).on("change", `[id^=${prefix}][id$=${suffix}]`, function () {
    const index = this.id.replace(prefix, "").replace(suffix, "");
    const suffix2Select = $(`#${prefix}${index}${suffix2}`);
    const suffix2SelectWrapper = suffix2Select.closest(".form-row");

    if (suffix2Select.data("init")) {
      suffix2Select.empty().trigger("change");
    } else {
      suffix2Select.data("init", "true");
    }

    if (this.value) {
      const autocompleteURL = suffix2Select.data("ajax--url");
      suffix2SelectWrapper.show();

      if (autocompleteURL && suffix2Select.select2) {
        const dataAjaxUrl = autocompleteURL.split("?")[0];
        suffix2Select.data("ajax--url", `${dataAjaxUrl}?parent_id=${this.value}`);
        suffix2Select.select2();
      }
    } else {
      suffix2SelectWrapper.hide();
    }
  });

  if (window.Tribute) {
    const tribute = new Tribute({
      values: function (text, cb) {
        const url = `/admin/questions/basequestion/autocomplete/?term=${text}`;
        $.get(url, function (data) {
          cb(data.results);
        });
      },
      trigger: "$",
      lookup: "text",
      fillAttr: "text",
      requireLeadingSpace: false,
      selectTemplate: (item) => {
        return "${" + item.original.text + "}";
      },
    });

    [
      document.getElementById("id_constraint"),
      document.getElementsByClassName("sub_question_constraint"),
      document.getElementById("id_relevant"),
      document.getElementsByClassName("sub_question_relevant"),
      document.getElementById("id_choice_filter"),
      document.getElementsByClassName("sub_question_choice_filter"),
      document.getElementById("id_calculation"),
      document.getElementsByClassName("sub_question_calculation"),
    ].forEach(function (target) {
      if (target && target.length !== 0) {
        tribute.attach(target);
      }
    });
  }

  if (!$("#id_constraint").val()) {
    $("#id_constraint_message")
      .val("")
      .closest(".field-constraint_message")
      .hide();
    $("#constraint_translations-group").hide();
  }

  $(".sub_question_constraint").each(function () {
    if (!$(this).val()) {
      const fieldset = $(this).closest("fieldset");
      fieldset
        .find(".field-constraint_message")
        .hide()
        .find(".sub_question_constraint_message")
        .val("");
      fieldset
        .closest(".inline-related")
        .find(".sub_question_constraint_translations-group")
        .hide();
    }
  });

  $("#id_constraint").on(
    "propertychange change keyup paste input",
    function () {
      if (!$(this).val()) {
        $("#id_constraint_message")
          .val("")
          .closest(".field-constraint_message")
          .hide();
        $("#constraint_translations-group").hide();
      } else {
        $("#id_constraint_message").closest(".field-constraint_message").show();
        $("#constraint_translations-group").show();
      }
    }
  );

  $(".sub_question_constraint").on(
    "propertychange change keyup paste input",
    function () {
      const fieldset = $(this).closest("fieldset");
      if (!$(this).val()) {
        fieldset
          .find(".field-constraint_message")
          .hide()
          .find(".sub_question_constraint_message")
          .val("");
        fieldset
          .closest(".inline-related")
          .find(".sub_question_constraint_translations-group")
          .hide();
      } else {
        fieldset.find(".field-constraint_message").show();
        fieldset
          .closest(".inline-related")
          .find(".sub_question_constraint_translations-group")
          .show();
      }
    }
  );
});
