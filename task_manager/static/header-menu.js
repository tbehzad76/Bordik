(function () {
  var toggle = document.getElementById('menu-toggle');
  var menu = document.getElementById('header-menu');
  if (!toggle || !menu) {
    return;
  }

  var MOBILE_BREAKPOINT = 820;

  function close() {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  }

  function open() {
    menu.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
  }

  function isOpen() {
    return menu.classList.contains('is-open');
  }

  toggle.addEventListener('click', function (event) {
    event.stopPropagation();
    if (isOpen()) {
      close();
    } else {
      open();
    }
  });

  menu.addEventListener('click', function (event) {
    if (event.target.tagName === 'A') {
      close();
    }
  });

  document.addEventListener('click', function (event) {
    if (!isOpen()) {
      return;
    }
    if (menu.contains(event.target) || toggle.contains(event.target)) {
      return;
    }
    close();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      close();
    }
  });

  window.addEventListener('resize', function () {
    if (window.innerWidth > MOBILE_BREAKPOINT && isOpen()) {
      close();
    }
  });
})();
