(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll("form[data-auto-submit]")
      .forEach(function (form) {
        form.querySelectorAll("input[data-toggle]").forEach(function (box) {
          box.addEventListener("change", function () {
            var name = box.getAttribute("data-toggle");
            var hidden = form.querySelector(
              'input[type="hidden"][name="' + name + '"]'
            );
            if (hidden) {
              hidden.value = box.checked ? "1" : "0";
            }
            form.submit();
          });
        });
      });
  });
})();
