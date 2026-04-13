document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;
  const relevantFields = [document.getElementById("id_relevant")]
    .concat(Array.from(document.querySelectorAll('[id$="-relevant"]')))
    .filter(Boolean);

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

  if (relevantFields.length) {
    tribute.attach(relevantFields);
  }
});
