document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;
  const initialName = $('#id_name').val();
  if (initialName) {
    const sfxSelect = $('#id_nested_suffixes');
    const autocompleteURL = sfxSelect.data('ajax--url');
    sfxSelect.data('ajax--url', `${autocompleteURL}?exclude_sfxs=${initialName}`).select2();
  }
});
