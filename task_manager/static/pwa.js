(function () {
  var installButton = document.getElementById('install-app');
  var modal = document.getElementById('install-modal');
  var installNow = document.getElementById('install-now');
  var dismissButton = document.getElementById('install-dismiss');
  var stepsList = document.getElementById('install-steps');

  var DISMISS_KEY = 'bordik-install-dismissed';
  var INSTALLED_KEY = 'bordik-installed';
  var POPUP_DELAY = 1200;

  var userAgent = window.navigator.userAgent || '';
  var isTouchPhone =
    /android|iphone|ipad|ipod/i.test(userAgent) ||
    window.matchMedia('(max-width: 820px)').matches;
  var isIos = /iphone|ipad|ipod/i.test(userAgent);
  var isSafari = /^((?!chrome|android|crios|fxios).)*safari/i.test(userAgent);
  var isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches ||
    window.navigator.standalone === true;
  var deferredPrompt = null;
  var installed = isStandalone || window.localStorage.getItem(INSTALLED_KEY) === '1';

  if (isStandalone) {
    document.documentElement.classList.add('is-standalone');
  }

  function markInstalled() {
    installed = true;
    try {
      window.localStorage.setItem(INSTALLED_KEY, '1');
    } catch (error) {
      /* private mode */
    }
    if (installButton) {
      installButton.hidden = true;
    }
    closeModal();
  }

  function closeModal() {
    if (modal && modal.open) {
      modal.close();
    }
  }

  function step(text) {
    var item = document.createElement('li');
    item.textContent = text;
    return item;
  }

  function renderIosSteps() {
    stepsList.hidden = false;
    stepsList.textContent = '';
    stepsList.appendChild(step('در Safari دکمهٔ «اشتراک‌گذاری» (مربع با فلش رو به بالا) را بزن.'));
    stepsList.appendChild(step('در فهرست باز شده، «Add to Home Screen» / «افزودن به صفحهٔ اصلی» را انتخاب کن.'));
    stepsList.appendChild(step('روی «Add» بزن؛ آیکون بوردیک روی صفحهٔ اصلی می‌آید.'));
  }

  function renderBrowserSteps() {
    stepsList.hidden = false;
    stepsList.textContent = '';
    stepsList.appendChild(step('منوی مرورگر را باز کن (سه نقطه در کروم یا سه خط در فایرفاکس).'));
    stepsList.appendChild(step('گزینهٔ «نصب برنامه» / «Install app» یا «افزودن به صفحهٔ اصلی» را بزن.'));
    stepsList.appendChild(step('تأیید کن؛ آیکون بوردیک روی صفحهٔ اصلی می‌آید.'));
  }

  function showModal() {
    if (!modal || installed || modal.open) {
      return;
    }
    if (installButton) {
      installButton.hidden = true;
    }
    if (stepsList) {
      stepsList.hidden = true;
      stepsList.textContent = '';
    }
    if (installNow) {
      installNow.hidden = !deferredPrompt;
    }
    if (isIos || isSafari) {
      renderIosSteps();
      if (installNow) {
        installNow.hidden = true;
      }
    }
    if (modal.showModal) {
      modal.showModal();
    } else {
      modal.setAttribute('open', 'open');
    }
  }

  function isDismissed() {
    try {
      return window.sessionStorage.getItem(DISMISS_KEY) === '1';
    } catch (error) {
      return false;
    }
  }

  function rememberDismissal() {
    try {
      window.sessionStorage.setItem(DISMISS_KEY, '1');
    } catch (error) {
      /* private mode */
    }
  }

  function schedulePopup() {
    if (installed || !modal || !isTouchPhone || isDismissed()) {
      return;
    }
    window.setTimeout(showModal, POPUP_DELAY);
  }

  function checkInstalled() {
    if (isStandalone) {
      return Promise.resolve(true);
    }
    if (typeof window.navigator.getInstalledRelatedApps === 'function') {
      return window.navigator
        .getInstalledRelatedApps()
        .then(function (apps) {
          return Array.isArray(apps) && apps.length > 0;
        })
        .catch(function () {
          return false;
        });
    }
    return Promise.resolve(false);
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    if (installed) {
      return;
    }
    if (installButton) {
      installButton.hidden = false;
    }
    if (modal && !modal.open && isTouchPhone) {
      showModal();
    }
  });

  window.addEventListener('appinstalled', markInstalled);

  if (installButton) {
    installButton.addEventListener('click', function () {
      if (deferredPrompt) {
        triggerNativePrompt();
        return;
      }
      showModal();
    });
  }

  if (installNow) {
    installNow.addEventListener('click', triggerNativePrompt);
  }

  if (dismissButton) {
    dismissButton.addEventListener('click', function () {
      rememberDismissal();
      closeModal();
    });
  }

  if (modal) {
    modal.addEventListener('cancel', function (event) {
      event.preventDefault();
      rememberDismissal();
      closeModal();
    });
    modal.addEventListener('click', function (event) {
      if (event.target === modal) {
        rememberDismissal();
        closeModal();
      }
    });
  }

  function triggerNativePrompt() {
    if (!deferredPrompt) {
      if (isIos) {
        renderIosSteps();
      } else {
        renderBrowserSteps();
      }
      return;
    }
    var prompt = deferredPrompt;
    deferredPrompt = null;
    if (installNow) {
      installNow.hidden = true;
    }
    prompt.prompt();
    prompt.userChoice.then(function () {
      closeModal();
    });
  }

  checkInstalled().then(function (alreadyInstalled) {
    if (alreadyInstalled) {
      markInstalled();
      return;
    }
    if (!isIos && typeof window.navigator.getInstalledRelatedApps === 'function') {
      installed = false;
      try {
        window.localStorage.removeItem(INSTALLED_KEY);
      } catch (error) {
        /* private mode */
      }
    }
    if (installed) {
      return;
    }
    if (installButton) {
      installButton.hidden = false;
    }
    schedulePopup();
  });
})();
