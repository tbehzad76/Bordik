/* Offline Jalali (Solar Hijri) date picker + conversion (no dependencies). */
(function () {
  "use strict";

  var BREAKS = [
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097,
    2192, 2262, 2324, 2394, 2456, 3178,
  ];

  function div(a, b) {
    return ~~(a / b);
  }

  function mod(a, b) {
    return a - ~~(a / b) * b;
  }

  function jalCal(jy) {
    var gy = jy + 621;
    var leapJ = -14;
    var jp = BREAKS[0];
    var jump = 0;
    var i;
    var jm;

    for (i = 1; i < BREAKS.length; i += 1) {
      jm = BREAKS[i];
      jump = jm - jp;
      if (jy < jm) {
        break;
      }
      leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4);
      jp = jm;
    }

    var n = jy - jp;
    leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
    if (mod(jump, 33) === 4 && jump - n === 4) {
      leapJ += 1;
    }

    var leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150;
    var march = 20 + leapJ - leapG;

    if (jump - n < 6) {
      n = n - jump + div(jump + 4, 33) * 33;
    }

    var leap = mod(mod(n + 1, 33) - 1, 4);
    if (leap === -1) {
      leap = 4;
    }

    return { leap: leap, gy: gy, march: march };
  }

  function g2d(gy, gm, gd) {
    var d =
      div((gy + div(gm - 8, 6) + 100100) * 1461, 4) +
      div(153 * mod(gm + 9, 12) + 2, 5) +
      gd -
      34840408;
    d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
    return d;
  }

  function d2g(jdn) {
    var j = 4 * jdn + 139361631;
    j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
    var i = div(mod(j, 1461), 4) * 5 + 308;
    var gd = div(mod(i, 153), 5) + 1;
    var gm = mod(div(i, 153), 12) + 1;
    var gy = div(j, 1461) - 100100 + div(8 - gm, 6);
    return { gy: gy, gm: gm, gd: gd };
  }

  function d2j(jdn) {
    var gy = d2g(jdn).gy;
    var jy = gy - 621;
    var r = jalCal(jy);
    var jdn1f = g2d(gy, 3, r.march);
    var k = jdn - jdn1f;
    var jm;
    var jd;

    if (k >= 0) {
      if (k <= 185) {
        jm = 1 + div(k, 31);
        jd = mod(k, 31) + 1;
        return { jy: jy, jm: jm, jd: jd };
      }
      k -= 186;
    } else {
      jy -= 1;
      k += 179;
      if (r.leap === 1) {
        k += 1;
      }
    }

    jm = 7 + div(k, 30);
    jd = mod(k, 30) + 1;
    return { jy: jy, jm: jm, jd: jd };
  }

  function j2d(jy, jm, jd) {
    var r = jalCal(jy);
    return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1;
  }

  function toJalaali(gy, gm, gd) {
    return d2j(g2d(gy, gm, gd));
  }

  function toGregorian(jy, jm, jd) {
    return d2g(j2d(jy, jm, jd));
  }

  function isLeapJalaali(jy) {
    return jalCal(jy).leap === 0;
  }

  function daysInMonth(jy, jm) {
    if (jm <= 6) {
      return 31;
    }
    if (jm <= 11) {
      return 30;
    }
    return isLeapJalaali(jy) ? 30 : 29;
  }

  function today() {
    var now = new Date();
    return toJalaali(now.getFullYear(), now.getMonth() + 1, now.getDate());
  }

  function pad(value) {
    return value < 10 ? "0" + value : String(value);
  }

  var MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
  ];
  var WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
  var PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
  var ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

  function toAsciiDigits(text) {
    return text.replace(/[۰-۹٠-٩]/g, function (char) {
      var index = PERSIAN_DIGITS.indexOf(char);
      if (index === -1) {
        index = ARABIC_DIGITS.indexOf(char);
      }
      return index === -1 ? char : String(index);
    });
  }

  function parseValue(text) {
    var value = toAsciiDigits(text || "").replace(/[-.\\]/g, "/").trim();
    if (!value) {
      return null;
    }
    var parts = value.split("/");
    if (parts.length !== 3) {
      return null;
    }
    var year = parseInt(parts[0], 10);
    var month = parseInt(parts[1], 10);
    var day = parseInt(parts[2], 10);
    if (!year || !month || !day) {
      return null;
    }
    if (year >= 1700) {
      return toJalaali(year, month, day);
    }
    if (month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) {
      return null;
    }
    return { jy: year, jm: month, jd: day };
  }

  function attach(input) {
    var picker = document.createElement("div");
    picker.className = "jalali-picker";
    picker.dir = "rtl";
    picker.hidden = true;
    document.body.appendChild(picker);

    var selected = parseValue(input.value);
    var initial = selected || today();
    var viewYear = initial.jy;
    var viewMonth = initial.jm;

    function valueOf() {
      return viewYear + "/" + pad(viewMonth) + "/" + pad(selected ? selected.jd : 1);
    }

    function render() {
      picker.innerHTML = "";

      var head = document.createElement("div");
      head.className = "jp-head";

      function navButton(label, deltaMonth, deltaYear) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "jp-nav";
        button.textContent = label;
        button.addEventListener("click", function () {
          var total = viewYear * 12 + (viewMonth - 1) + deltaMonth + deltaYear * 12;
          viewYear = Math.floor(total / 12);
          viewMonth = (total % 12) + 1;
          render();
        });
        return button;
      }

      head.appendChild(navButton("»", 0, -1));
      head.appendChild(navButton("›", -1, 0));

      var title = document.createElement("span");
      title.className = "jp-title";
      title.textContent = MONTHS[viewMonth - 1] + " " + viewYear;
      head.appendChild(title);

      head.appendChild(navButton("‹", 1, 0));
      head.appendChild(navButton("«", 0, 1));
      picker.appendChild(head);

      var grid = document.createElement("div");
      grid.className = "jp-grid";
      WEEKDAYS.forEach(function (day) {
        var cell = document.createElement("span");
        cell.className = "jp-dow";
        cell.textContent = day;
        grid.appendChild(cell);
      });

      var first = toGregorian(viewYear, viewMonth, 1);
      var startColumn = (new Date(first.gy, first.gm - 1, first.gd).getDay() + 1) % 7;
      var total = daysInMonth(viewYear, viewMonth);
      var i;

      for (i = 0; i < startColumn; i += 1) {
        var empty = document.createElement("span");
        empty.className = "jp-empty";
        grid.appendChild(empty);
      }

      for (i = 1; i <= total; i += 1) {
        (function (dayNumber) {
          var button = document.createElement("button");
          button.type = "button";
          button.className = "jp-day";
          button.textContent = dayNumber;
          if (
            selected &&
            selected.jy === viewYear &&
            selected.jm === viewMonth &&
            selected.jd === dayNumber
          ) {
            button.classList.add("is-selected");
          }
          button.addEventListener("click", function () {
            selected = { jy: viewYear, jm: viewMonth, jd: dayNumber };
            input.value = viewYear + "/" + pad(viewMonth) + "/" + pad(dayNumber);
            input.dispatchEvent(new Event("change", { bubbles: true }));
            close();
          });
          grid.appendChild(button);
        })(i);
      }

      picker.appendChild(grid);

      var actions = document.createElement("div");
      actions.className = "jp-actions";

      var todayButton = document.createElement("button");
      todayButton.type = "button";
      todayButton.className = "jp-action";
      todayButton.textContent = "امروز";
      todayButton.addEventListener("click", function () {
        var now = today();
        viewYear = now.jy;
        viewMonth = now.jm;
        selected = now;
        input.value = now.jy + "/" + pad(now.jm) + "/" + pad(now.jd);
        input.dispatchEvent(new Event("change", { bubbles: true }));
        close();
      });
      actions.appendChild(todayButton);

      var clearButton = document.createElement("button");
      clearButton.type = "button";
      clearButton.className = "jp-action";
      clearButton.textContent = "پاک کردن";
      clearButton.addEventListener("click", function () {
        selected = null;
        input.value = "";
        input.dispatchEvent(new Event("change", { bubbles: true }));
        close();
      });
      actions.appendChild(clearButton);

      picker.appendChild(actions);
    }

    function position() {
      var rect = input.getBoundingClientRect();
      var top = window.scrollY + rect.bottom + 6;
      var left = window.scrollX + rect.left;
      var maxLeft = window.scrollX + document.documentElement.clientWidth - 270;
      picker.style.top = top + "px";
      picker.style.left = Math.max(8, Math.min(left, maxLeft)) + "px";
    }

    function open() {
      var parsed = parseValue(input.value);
      if (parsed) {
        selected = parsed;
        viewYear = parsed.jy;
        viewMonth = parsed.jm;
      } else {
        var now = today();
        viewYear = now.jy;
        viewMonth = now.jm;
      }
      render();
      picker.hidden = false;
      position();
    }

    function close() {
      picker.hidden = true;
    }

    input.addEventListener("focus", open);
    input.addEventListener("click", open);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        close();
      }
    });

    document.addEventListener("click", function (event) {
      if (picker.hidden) {
        return;
      }
      if (event.target === input || picker.contains(event.target)) {
        return;
      }
      close();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var inputs = document.querySelectorAll("input[data-jalali]");
    for (var i = 0; i < inputs.length; i += 1) {
      attach(inputs[i]);
    }
  });
})();
