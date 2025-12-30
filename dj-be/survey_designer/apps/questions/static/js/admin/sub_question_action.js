document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;
  $('input[name=_addanother]').hide();
  $('input[name=_continue]').hide();

  const urlParams = new URLSearchParams(window.location.search);
  const ids = urlParams.get('ids') || '';
  $('#id_root_question_ids').val(ids);

  const names = urlParams.get('names') || '';
  const namesDisplay = names.replace(',', ', ');
  $('#content h1').first().html(`Add Sub Question to: <strong>${namesDisplay}</strong>`);

  $(document).on('change', '#id_suffix', function () {
    const suffix2Select = $('#id_suffix_2');
    const suffix2SelectWrapper = suffix2Select.closest('.form-row');

    suffix2Select.empty().trigger('change');

    if (this.value) {
      const dataAjaxUrl = suffix2Select.data('ajax--url').split('?')[0];
      suffix2SelectWrapper.show();
      suffix2Select.data('ajax--url', `${dataAjaxUrl}?parent_id=${this.value}`);
      suffix2Select.select2();
    } else {
      suffix2SelectWrapper.hide();
    }
  });
});
