document.addEventListener("DOMContentLoaded", function () {
  if (!window.jalaliDatepicker) {
    return;
  }
  window.jalaliDatepicker.startWatch({
    time: false,
    persianDigits: true,
    autoShow: true,
    autoHide: true,
    hideAfterChange: true,
    selector: "input[data-jdp]",
  });
});
