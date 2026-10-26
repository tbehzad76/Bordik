(function () {
  var root = document.getElementById("notif");
  if (!root) {
    return;
  }

  var feedUrl = root.dataset.feedUrl;
  var readUrl = root.dataset.readUrl;
  var csrfToken = root.dataset.csrf;
  var bell = document.getElementById("notif-bell");
  var count = document.getElementById("notif-count");
  var panel = document.getElementById("notif-panel");
  var list = document.getElementById("notif-list");
  var enable = document.getElementById("notif-enable");
  var hint = document.getElementById("notif-hint");

  var lastSeen = Number(window.localStorage.getItem("bordik_last_notif") || 0);
  var firstLoad = true;

  function supportsNotifications() {
    return "Notification" in window;
  }

  function isSecureContext() {
    return window.isSecureContext || location.hostname === "localhost" || location.hostname === "127.0.0.1";
  }

  function showHint(message) {
    if (!hint) {
      return;
    }
    hint.textContent = message;
    hint.hidden = false;
  }

  function updateEnableButton() {
    if (!enable) {
      return;
    }
    if (!supportsNotifications() || !isSecureContext()) {
      enable.hidden = true;
      showHint("اعلان مرورگر فقط روی HTTPS (یا localhost) کار می‌کند. برای استفاده از اعلان بومی، سایت را با HTTPS باز کن.");
      return;
    }
    if (Notification.permission === "granted") {
      enable.hidden = true;
      return;
    }
    enable.hidden = false;
    if (Notification.permission === "denied") {
      showHint("مجوز اعلان در مرورگر بسته است. از تنظیمات سایت در مرورگر، اعلان را روی «اجازه» بگذار و صفحه را رفرش کن.");
    }
  }

  function updateCount(unread) {
    if (!count) {
      return;
    }
    if (unread > 0) {
      count.textContent = unread > 9 ? "9+" : String(unread);
      count.hidden = false;
    } else {
      count.hidden = true;
    }
  }

  function renderList(items) {
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!items.length) {
      var empty = document.createElement("li");
      empty.className = "notif-empty";
      empty.textContent = "اعلانی نداری.";
      list.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "notif-item" + (item.is_read ? "" : " is-unread");
      var link = document.createElement("a");
      link.href = item.url || "/my-tasks";
      link.textContent = item.title;
      li.appendChild(link);
      if (item.body) {
        var body = document.createElement("p");
        body.className = "notif-body";
        body.textContent = item.body;
        li.appendChild(body);
      }
      list.appendChild(li);
    });
  }

  function showBrowserNotifications(items) {
    if (!supportsNotifications() || Notification.permission !== "granted") {
      return;
    }
    items.forEach(function (item) {
      try {
        var notification = new Notification(item.title, {
          body: item.body || "",
        });
        notification.onclick = function () {
          window.focus();
          if (item.url) {
            window.location.href = item.url;
          }
        };
      } catch (error) {
        console.error(error);
      }
    });
  }

  async function poll() {
    try {
      var response = await fetch(feedUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) {
        return;
      }
      var data = await response.json();
      renderList(data.items || []);
      updateCount(data.unread || 0);

      var newest = data.items && data.items.length ? data.items[0].id : 0;
      if (firstLoad) {
        if (!lastSeen) {
          lastSeen = newest;
          window.localStorage.setItem("bordik_last_notif", String(lastSeen));
        }
        firstLoad = false;
        return;
      }
      if (newest > lastSeen) {
        var fresh = (data.items || []).filter(function (item) {
          return item.id > lastSeen;
        });
        showBrowserNotifications(fresh);
        lastSeen = newest;
        window.localStorage.setItem("bordik_last_notif", String(lastSeen));
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function markAllRead() {
    try {
      await fetch(readUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ all: true }),
      });
    } catch (error) {
      console.error(error);
    }
    updateCount(0);
    document.querySelectorAll(".notif-item.is-unread").forEach(function (item) {
      item.classList.remove("is-unread");
    });
  }

  if (bell && panel) {
    bell.addEventListener("click", function () {
      var opening = panel.hidden;
      panel.hidden = !panel.hidden;
      if (opening) {
        markAllRead();
      }
    });
    document.addEventListener("click", function (event) {
      if (!panel.hidden && !root.contains(event.target)) {
        panel.hidden = true;
      }
    });
  }

  if (enable) {
    enable.addEventListener("click", function () {
      if (!supportsNotifications() || !isSecureContext()) {
        updateEnableButton();
        return;
      }
      var result = Notification.requestPermission();
      if (result && typeof result.then === "function") {
        result.then(handlePermission);
      }
    });
  }

  function handlePermission(permission) {
    updateEnableButton();
    if (permission === "granted") {
      showHint("اعلان مرورگر فعال شد.");
      try {
        new Notification("اعلان فعال شد", {
          body: "از این پس وظایف جدید برای تو اینجا نمایش داده می‌شوند.",
        });
      } catch (error) {
        console.error(error);
      }
    } else if (permission === "denied") {
      showHint("مجوز اعلان بسته شد. از تنظیمات سایت در مرورگر، اعلان را «اجازه» کن.");
    }
  }

  updateEnableButton();
  poll();
  window.setInterval(poll, 20000);
})();
