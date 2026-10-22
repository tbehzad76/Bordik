(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll("form[data-auto-submit]")
      .forEach(function (form) {
        form.querySelectorAll('input[type="checkbox"]').forEach(function (box) {
          box.addEventListener("change", function () {
            form.submit();
          });
        });
      });
  });
})();
