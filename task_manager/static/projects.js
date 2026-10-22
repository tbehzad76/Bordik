(function () {
  var dialog = document.getElementById("project-modal");
  if (!dialog) {
    return;
  }

  function open() {
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "open");
    }
  }

  function close() {
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
  }

  document.querySelectorAll("[data-open-project-modal]").forEach(function (button) {
    button.addEventListener("click", open);
  });

  document.querySelectorAll("[data-close-project-modal]").forEach(function (button) {
    button.addEventListener("click", close);
  });

  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) {
      close();
    }
  });
})();
