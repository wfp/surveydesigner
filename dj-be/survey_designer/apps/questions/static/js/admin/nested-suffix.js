document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;
  $('input[name=_addanother]').hide();
  $('input[name=_continue]').hide();
  const urlParams = new URLSearchParams(window.location.search);
  const sfxs = urlParams.get('sfxs') || '';
  const sfxsDisplay = sfxs.replace(',', ', ');
  $('#id_suffixes').val(sfxs);
  $('#content h1').first().html(`Add nested suffix to: <strong>${sfxsDisplay}</strong>`);
  const sfxSelect = $('#id_nested_suffixes');
  const autocompleteURL = sfxSelect.data('ajax--url');
  sfxSelect.data('ajax--url', `${autocompleteURL}?exclude_sfxs=${sfxs}`).select2();
});
