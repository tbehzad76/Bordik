(function () {
  var installButton = document.getElementById('install-app');
  var isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  var isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
  var deferredPrompt = null;

  function hideInstallButton() {
    if (installButton) {
      installButton.hidden = true;
    }
  }

  function showInstallButton(label) {
    if (!installButton) {
      return;
    }
    installButton.textContent = label;
    installButton.hidden = false;
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  if (isStandalone) {
    document.documentElement.classList.add('is-standalone');
  }

  if (!installButton) {
    return;
  }

  if (isStandalone) {
    hideInstallButton();
  } else if (isIos) {
    showInstallButton('نصب روی صفحه اصلی');
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    showInstallButton('نصب روی صفحه اصلی');
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    hideInstallButton();
  });

  installButton.addEventListener('click', function () {
    if (deferredPrompt) {
      var prompt = deferredPrompt;
      deferredPrompt = null;
      prompt.prompt();
      prompt.userChoice.then(function () {
        hideInstallButton();
      });
      return;
    }
    var hint = document.getElementById('install-hint');
    if (hint) {
      hint.hidden = !hint.hidden;
    }
  });
})();
