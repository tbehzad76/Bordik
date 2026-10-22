(function () {
  function validate(form) {
    var boxes = form.querySelectorAll('input[name="assignee_ids"]');
    if (!boxes.length) {
      return true;
    }
    var anyChecked = Array.prototype.some.call(boxes, function (box) {
      return box.checked;
    });
    var error = form.querySelector("[data-assignee-error]");
    if (!anyChecked) {
      if (error) {
        error.hidden = false;
      }
      form.classList.add("has-error");
      return false;
    }
    if (error) {
      error.hidden = true;
    }
    form.classList.remove("has-error");
    return true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll("form[data-require-assignee]")
      .forEach(function (form) {
        form.addEventListener("submit", function (event) {
          if (!validate(form)) {
            event.preventDefault();
          }
        });
      });
  });
})();
