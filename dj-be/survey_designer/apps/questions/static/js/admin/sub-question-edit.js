document.addEventListener("DOMContentLoaded", function () {
  const $ = django.jQuery;

  $(document).on("change", "#id_suffix", function () {
    const suffix2Select = $("#id_suffix_2");
    const suffix2SelectWrapper = suffix2Select.closest(".form-row");

    if (suffix2Select.data("init")) {
      suffix2Select.empty().trigger("change");
    } else {
      suffix2Select.data("init", "true");
    }

    if (this.value) {
      const dataAjaxUrl = suffix2Select.data("ajax--url").split("?")[0];
      suffix2SelectWrapper.show();
      suffix2Select.data("ajax--url", `${dataAjaxUrl}?parent_id=${this.value}`);
      suffix2Select.select2();
    } else {
      suffix2SelectWrapper.hide();
    }
  });

  var tribute = new Tribute({
    values: function (text, cb) {
      const url = `/admin/questions/basequestion/autocomplete/?q=${text}`;
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

  tribute.attach(document.getElementById("id_constraint"));
  tribute.attach(document.getElementById("id_relevant"));
  tribute.attach(document.getElementById("id_choice_filter"));
  tribute.attach(document.getElementById("id_calculation"));

  if (!$("#id_constraint").val()) {
    $("#id_constraint_message")
      .val("")
      .closest(".field-constraint_message")
      .hide();
    $("#constraint_translations-group").hide();
  }

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
});
