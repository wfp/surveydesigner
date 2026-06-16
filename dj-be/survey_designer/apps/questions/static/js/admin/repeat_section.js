document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;

  const tributeTargets = [
    document.getElementById("id_repeat_count"),
    document.getElementById("id_relevant"),
  ].filter(Boolean);

  if (window.Tribute && tributeTargets.length) {
    var tribute = new Tribute({
      values: function (text, cb) {
        const url = `/admin/questions/basequestion/autocomplete/?term=${text}`;
        $.get(url, function (data) {
          cb(data.results);
        });
      },
      trigger: '$',
      lookup: 'text',
      fillAttr: 'text',
      requireLeadingSpace: false,
      selectTemplate: (item) => {
        return '${' + item.original.text + '}';
      },
    });

    tributeTargets.forEach(function (target) {
      tribute.attach(target);
    });
  }
});
