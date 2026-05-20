(function () {
  'use strict';

  function formatHoursRemaining(ms) {
    if (ms <= 0) return '0';
    return String(Math.ceil(ms / 3600000));
  }

  function initPostDailyLimitTimer(alertEl) {
    if (!alertEl) return;
    const resetAt = alertEl.getAttribute('data-reset-at');
    const timerEl = alertEl.querySelector('[data-post-limit-timer]');
    if (!resetAt || !timerEl) return;

    let intervalId = null;

    function tick() {
      const diff = new Date(resetAt).getTime() - Date.now();
      timerEl.textContent = formatHoursRemaining(diff);
      if (diff <= 0 && intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }

    tick();
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(tick, 60000);
  }

  function initAllPostDailyLimitTimers(root) {
    (root || document).querySelectorAll('#postDailyLimitAlert[data-reset-at]').forEach(initPostDailyLimitTimer);
  }

  window.initPostDailyLimitTimer = initPostDailyLimitTimer;
  window.initAllPostDailyLimitTimers = initAllPostDailyLimitTimers;

  document.addEventListener('DOMContentLoaded', function () {
    initAllPostDailyLimitTimers(document);
  });
})();
