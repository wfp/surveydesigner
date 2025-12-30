document.addEventListener('DOMContentLoaded', function() {
  const $ = django.jQuery;
  const categories = JSON.parse($('#id_category_to_type').val());

  const typeToAttributes = categories
    .flatMap(cat => cat.survey_types)
    .reduce((obj, item) => {
      obj[item.id] = item.attributes;
      return obj;
    }, {});

  const urlParams = new URLSearchParams(window.location.search);
  const toggleOff = urlParams.get('toggle_off');

  function includeCheckboxSwitch(elem, checked) {
    if (!checked) {
      elem
        .closest('.form-wrapper')
        .find('.to-toggle')
        .hide()
        .find('.delete input')
        .prop('checked', true);
    } else {
      elem
        .closest('.form-wrapper')
        .find('.to-toggle')
        .show()
        .find('.delete input')
        .prop('checked', false);
    }
  }

  function toggleTypes(id, checked, init) {
    const typeIDs = categories
      .filter(category => category.id === id)
      .flatMap(category => category.survey_types)
      .map(type => type.id)
      .forEach(typeID => {
        let typeElem = $(`.survey-type-wrapper[data-id="${typeID}"] .include-checkbox`);

        if (!init) {
          typeElem.prop('checked', checked);
          includeCheckboxSwitch(typeElem, checked);
        } else if (!checked) {
          typeElem.prop('checked', checked);
          includeCheckboxSwitch(typeElem, checked);
        }
        typeElem = typeElem.closest('.survey-type-wrapper');

        if (!toggleOff) {
          if (checked) {
            typeElem.show();
          } else {
            typeElem.hide();
          }
        }
      });
  }

  function toggleAttributes(init) {
    const selectedTypes = [
      ...$('.survey-types .include-checkbox:checked')
        .closest('.form-wrapper')
        .find('.survey-type input')
        .map(function() {
          return parseInt(this.value);
        })
    ];

    const attrs = new Set();
    selectedTypes.forEach(typeID => {
      typeToAttributes[typeID].forEach(attr => attrs.add(attr.id));
    });

    $('.survey-attribute input').each(function() {
      const checked = attrs.has(parseInt($(this).val()));

      let attrElem = $(this)
        .closest('.survey-attribute-wrapper')
        .find('.include-checkbox');

      if (!init) {
        attrElem.prop('checked', checked);
        includeCheckboxSwitch(attrElem, checked);
      } else if (!checked) {
        attrElem.prop('checked', checked);
        includeCheckboxSwitch(attrElem, checked);
      }

      attrElem = attrElem.closest('.survey-attribute-wrapper');

      if (!toggleOff) {
        if (checked) {
          attrElem.show();
        } else {
          attrElem.hide();
        }
      }
    });
  }

  toggleAttributes(true);

  const surveyCategories = $('.survey-categories .include-checkbox');
  surveyCategories.each(function () {
    const value = parseInt($(this).closest('.form-wrapper').find('.survey-category input').val());
    toggleTypes(value, $(this).prop('checked'), true);
  });
  surveyCategories.change(function (event) {
    const value = parseInt($(this).closest('.form-wrapper').find('.survey-category input').val());
    toggleTypes(value, event.target.checked);
    toggleAttributes();
  });

  $('.include-checkbox').each(function () {
    if (!$(this).prop('checked')) {
      $(this).closest('.form-wrapper').find('.to-toggle').hide();
    }
  });

  $('.include-checkbox').change(function (event) {
    includeCheckboxSwitch($(this), event.target.checked);
  });

  const surveyTypes = $('.survey-types .include-checkbox');

  surveyTypes.change(function (event) {
    toggleAttributes();
  });
});
