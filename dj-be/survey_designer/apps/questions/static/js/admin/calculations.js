document.addEventListener('DOMContentLoaded', function () {
  const $ = django.jQuery;

  const calculationInput = document.getElementById("id_calculation");

  if (window.Tribute && calculationInput) {
    var tribute = new Tribute({
      values: function (text, cb) {
        const url = `/admin/questions/basequestion/autocomplete/?term=${text}&types=integer,decimal,date`;
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

    tribute.attach(calculationInput);
  }
});
