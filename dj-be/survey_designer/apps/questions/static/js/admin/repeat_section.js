document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;

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

  tribute.attach(document.getElementById("id_repeat_count"));
  tribute.attach(document.getElementById("id_relevant"));
});
