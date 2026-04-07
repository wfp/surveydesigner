(function () {
  if (!window.django || !window.django.jQuery) {
    return;
  }

  window.jQuery = window.django.jQuery;
  window.$ = window.django.jQuery;
})();
