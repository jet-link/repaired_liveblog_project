window.LB = window.LB || {};

/* Safe if global_utils runs twice; re-runnable on turbo:load for new DOM. */
function lbInitBootstrapDataToggleTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    var nodes = document.querySelectorAll('[data-bs-toggle="tooltip"], [data-bs-title]');
    if (!nodes.length) return;
    Array.prototype.forEach.call(nodes, function (el) {
        if (el.__lbBsTooltipBound) return;
        el.__lbBsTooltipBound = true;
        try {
            new bootstrap.Tooltip(el);
        } catch (e) { /* ignore */ }
    });
}
LB.initDataToggleTooltips = lbInitBootstrapDataToggleTooltips;
lbInitBootstrapDataToggleTooltips();
(document.documentElement || document).addEventListener('turbo:load', function () {
    lbInitBootstrapDataToggleTooltips();
});

/* ── iOS-safe scroll lock ──
   Uses position:fixed on body so Safari doesn't scroll through overlays.
   Keeps track of nested lock/unlock calls via a counter. */
var _scrollLockCount = 0;
var _scrollLockY = 0;
function lockScroll() {
    if (_scrollLockCount === 0) {
        var se = document.scrollingElement || document.documentElement;
        var st = se ? Math.round(se.scrollTop) : 0;
        var wy = Math.round(window.scrollY || window.pageYOffset || 0);
        _scrollLockY = Math.max(0, st, wy);
        document.documentElement.style.setProperty('--scroll-y', '-' + _scrollLockY + 'px');
        document.documentElement.classList.add('scroll-locked');
    }
    _scrollLockCount++;
}
function unlockScroll() {
    if (_scrollLockCount <= 0) {
        return;
    }
    _scrollLockCount -= 1;
    if (_scrollLockCount === 0) {
        const y = Math.max(0, Number(_scrollLockY) || 0);
        document.documentElement.classList.remove('scroll-locked');
        document.documentElement.style.removeProperty('--scroll-y');
        /* Synchronous restore: deferring scrollTo one frame lets the browser paint at scroll 0 (visible jump). */
        const root = document.documentElement;
        const prevBehavior = root.style.scrollBehavior;
        root.style.scrollBehavior = 'auto';
        window.scrollTo({ left: 0, top: y, behavior: 'auto' });
        var se = document.scrollingElement || document.documentElement;
        if (se) {
            se.scrollTop = y;
        }
        if (prevBehavior) {
            root.style.scrollBehavior = prevBehavior;
        } else {
            root.style.removeProperty('scroll-behavior');
        }
    }
}

/**
 * Turbo replaces `<body>` but not `<html>`. If an overlay called lockScroll() and the
 * old body was removed, `html.scroll-locked` still applies to the new body (position:fixed),
 * which breaks page scrolling until a full reload.
 */
function resetScrollLockAfterTurboNavigation() {
    if (_scrollLockCount === 0 && !document.documentElement.classList.contains('scroll-locked')) {
        return;
    }
    _scrollLockCount = 0;
    document.documentElement.classList.remove('scroll-locked');
    document.documentElement.style.removeProperty('--scroll-y');
}

(document.documentElement || document).addEventListener('turbo:load', resetScrollLockAfterTurboNavigation);

/* bfcache restore: same stale html.scroll-locked as Turbo body swap, but without turbo:load */
window.addEventListener('pageshow', function (ev) {
    if (!ev.persisted) return;
    if (_scrollLockCount === 0 && !document.documentElement.classList.contains('scroll-locked')) return;
    resetScrollLockAfterTurboNavigation();
});

function initAutoDismiss(container, onAfterRemove) {
    const root = container || document;
    const path = typeof window !== 'undefined' ? window.location.pathname : '';
    const isSmartBlogPage = path.startsWith('/blog/') || path.startsWith('/search/') || path.startsWith('/post/');
    let els = root.querySelectorAll ? Array.from(root.querySelectorAll('[data-auto-dismiss]')) : [];
    if (root.nodeType === 1 && root.matches && root.matches('[data-auto-dismiss]') && !els.includes(root)) {
        els.unshift(root);
    }
    els.forEach(function (el) {
        if (el.__autoDismissInit) return;
        if (isSmartBlogPage) return;
        el.__autoDismissInit = true;
        // const ms = parseInt(el.getAttribute('data-auto-dismiss'), 10) || 3000;
        // setTimeout(function () {
        //     el.style.transition = 'opacity 0.3s ease';
        //     el.style.opacity = '0';
        //     setTimeout(function () {
        //         el.remove();
        //         if (typeof onAfterRemove === 'function') onAfterRemove();
        //     }, 300);
        // }, ms);
    });
}
window.initAutoDismiss = initAutoDismiss;
LB.lockScroll = lockScroll;
LB.unlockScroll = unlockScroll;
LB.resetScrollLockAfterTurboNavigation = resetScrollLockAfterTurboNavigation;
LB.initAutoDismiss = initAutoDismiss;

/* Bootstrap modals: same iOS-safe scroll lock as gallery / overlays (backdrop must not scroll). */
document.addEventListener('show.bs.modal', function (e) {
    if (e.defaultPrevented) return;
    lockScroll();
}, false);
document.addEventListener('hidden.bs.modal', function () {
    unlockScroll();
}, false);

document.addEventListener('DOMContentLoaded', function () {
    initAutoDismiss(document);
});



document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.ck-content table').forEach(function (t) {
        t.classList.add('table', 'table-bordered', 'table-striped');
    });
});

// Notifications bell count (sync from localStorage)
(function () {
    'use strict';

    const STALE_MS = 90000;

    function updateBellCountFromStorage(forceCount) {
        const btns = document.querySelectorAll('.notification-btn');
        if (!btns.length) return;

        if (typeof forceCount !== 'number' && document.getElementById('notificationsState')) {
            return;
        }

        let count;
        if (typeof forceCount === 'number' && !Number.isNaN(forceCount)) {
            count = Math.max(0, Math.floor(forceCount));
            try {
                localStorage.setItem('notification_unread_count', String(count));
                localStorage.setItem('notification_count_updated_at', String(Date.now()));
            } catch (err) {}
        } else {
            let stored = null;
            let updatedAt = null;
            try {
                stored = localStorage.getItem('notification_unread_count');
                updatedAt = localStorage.getItem('notification_count_updated_at');
            } catch (err) {}

            const serverRaw = btns[0].dataset?.notificationsCount;
            const serverCount = serverRaw !== undefined && serverRaw !== null && serverRaw !== ''
                ? parseInt(serverRaw, 10)
                : NaN;
            const storedCount = stored !== null ? parseInt(stored, 10) : NaN;

            if (!Number.isNaN(serverCount) && !Number.isNaN(storedCount)) {
                const ts = updatedAt ? parseInt(updatedAt, 10) : 0;
                const isRecent = ts && (Date.now() - ts) < STALE_MS;
                if (storedCount === 0 && serverCount > 0) {
                    count = serverCount;
                } else {
                    count = isRecent ? Math.min(serverCount, storedCount) : serverCount;
                }
            } else if (!Number.isNaN(serverCount)) {
                count = serverCount;
            } else if (!Number.isNaN(storedCount)) {
                count = storedCount;
            } else {
                return;
            }

            try {
                localStorage.setItem('notification_unread_count', String(count));
            } catch (err) {}
        }

        btns.forEach(function (btn) {
            if (count > 0) {
                btn.classList.add('has-unread');
            } else {
                btn.classList.remove('has-unread');
            }
        });
    }

    window.updateBellCountFromStorage = updateBellCountFromStorage;

    document.addEventListener('DOMContentLoaded', updateBellCountFromStorage);
    window.addEventListener('pageshow', updateBellCountFromStorage);
    window.addEventListener('storage', function (e) {
        if (e.key === 'notification_unread_count') {
            updateBellCountFromStorage();
        }
    });

    document.addEventListener('click', function (e) {
        const a = e.target.closest?.('a[href*="logout"]');
        if (a) {
            try {
                localStorage.removeItem('notification_unread_count');
                localStorage.removeItem('notification_count_updated_at');
            } catch (err) {}
        }
    }, true);
})();

// Replace broken avatar images with fallback
(function () {
    'use strict';

    const FALLBACK_AVATAR = '/static/img/no_image.svg';

    function applyAvatarFallback(img) {
        if (!img || img.dataset?.avatarFallbackApplied) return;
        img.dataset.avatarFallbackApplied = '1';
        img.onerror = null;
        img.src = FALLBACK_AVATAR;
    }

    // Capture load errors for avatar images
    window.addEventListener('error', function (e) {
        const target = e.target;
        if (target && target.tagName === 'IMG' && target.classList.contains('user-avatar')) {
            applyAvatarFallback(target);
        }
    }, true);
})();

// static/js/select_auto_size.js
(function () {
    'use strict';

    // Обновляет size для одного select
    function updateSelectSize(select, maxSize) {
        if (!select) return;
        // count only non-disabled options? here we count all options
        var optsCount = select.options ? select.options.length : 0;
        var desired = Math.min(Math.max(optsCount, 1), maxSize || 8);
        // If select имеет native multiple, устанавливаем size; иначе ничего не делаем
        try {
            if (select.multiple) {
                // избегаем ненужного перерендера
                if (String(select.size) !== String(desired)) {
                    select.size = desired;
                }
            } else {
                // если не multiple — ничего
                select.size = 0;
            }
        } catch (e) {
            // ignore
            console.error('updateSelectSize error', e);
        }
    }

    // Инициализация: находит все select.auto-size-select с data-auto-size
    function initAutoSizeSelects() {
        var selects = Array.prototype.slice.call(document.querySelectorAll('select.auto-size-select'));
        selects.forEach(function (sel) {
            try {
                var max = parseInt(sel.getAttribute('data-max-size') || sel.dataset.maxSize || 8, 10) || 8;
                updateSelectSize(sel, max);

                // следим за изменениями (если опции добавляются динамически)
                // MutationObserver следит за изменением списка option внутри select
                if (window.MutationObserver) {
                    var mo = new MutationObserver(function (mutList) {
                        // на любое изменение childList -> обновляем
                        updateSelectSize(sel, max);
                    });
                    mo.observe(sel, { childList: true, subtree: false });
                    // сохраняем ссылку чтобы при необходимости остановить наблюдение
                    sel.__autoSizeObserver = mo;
                }

                // Также подпишемся на кастомное событие 'auto-size:update' чтобы можно было вручную триггерить
                sel.addEventListener('auto-size:update', function (e) {
                    updateSelectSize(sel, max);
                });

                // optional: при изменении опций (например, пользователь выбрал/добавил теги через внешний UI),
                // вызывайте document.querySelector('select.auto-size-select').dispatchEvent(new Event('auto-size:update'));
            } catch (err) {
                console.error('auto-size init error', err);
            }
        });
    }

    // Инициализация при DOMContentLoaded и pageshow (bfcache)
    document.addEventListener('DOMContentLoaded', initAutoSizeSelects);
    window.addEventListener('pageshow', initAutoSizeSelects);

    // expose helper to window so you can call it manually if needed
    window.__autoSizeSelects = {
        updateAll: initAutoSizeSelects,
        updateOne: function (selector) {
            var sel = document.querySelector(selector);
            if (sel) sel.dispatchEvent(new Event('auto-size:update'));
        }
    };
})();


// Share button
document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const modalEl = document.getElementById('shareItemModal');
    const copyBtn = document.getElementById('copyShareLinkBtn');
    const linkInput = document.getElementById('shareLinkInput');
    const feedback = document.getElementById('shareCopyFeedback');

    let lastTrigger = null;

    function showShareItemModal(triggerEl) {
        if (!modalEl) return;
        if (triggerEl) lastTrigger = triggerEl;
        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
        bsModal.show();
        setTimeout(() => {
            if (linkInput) {
                try { linkInput.select(); } catch (err) { }
            }
        }, 250);
    }

    document.querySelectorAll('.item_share_btn').forEach(el => {
        el.addEventListener('click', function (e) {
            e.preventDefault();
            showShareItemModal(el);
        });
    });

    window.addEventListener('open-post-share-modal', function (ev) {
        const t = ev.detail && ev.detail.trigger;
        showShareItemModal(t || null);
    });

    // Repost API: send repost event, update counter
    function humanCount(n) {
        n = Number(n);
        if (isNaN(n) || n < 0) return '0';
        if (n < 1000) return String(n);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
        if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
        return String(n);
    }
    function getCookie(name) {
        return document.cookie.split('; ').find(c => c.startsWith(name + '='))?.split('=')[1];
    }
    async function sendRepost(platform) {
        const itemId = document.body.dataset.itemId;
        if (!itemId) return null;
        const apiUrl = (modalEl && modalEl.dataset.repostApi) || '/blog/api/repost/';
        try {
            const r = await fetch(apiUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ post_id: itemId, platform })
            });
            const data = await r.json().catch(() => ({}));
            const count = data.reposts_count;
            if (typeof count === 'number') {
                const repostEl = document.getElementById('repostCount');
                if (repostEl) repostEl.textContent = humanCount(count);
                const cardEl = document.getElementById('reposts-count-' + itemId);
                if (cardEl) cardEl.textContent = humanCount(count);
                try {
                    const changes = JSON.parse(sessionStorage.getItem('listing_changes') || '{}');
                    changes[itemId] = changes[itemId] || {};
                    changes[itemId].reposts_count = count;
                    sessionStorage.setItem('listing_changes', JSON.stringify(changes));
                } catch (e) { }
                return count;
            }
        } catch (e) { console.warn('Repost API error', e); }
        return null;
    }

    // Copy to clipboard + repost
    if (copyBtn && linkInput) {
        copyBtn.addEventListener('click', async function (e) {
            e.preventDefault();
            const text = linkInput.value || '';
            if (!text) return;
            await sendRepost('copy_link');
            try {
                await navigator.clipboard.writeText(text);
                showFeedback();
            } catch (err) {
                try {
                    linkInput.select();
                    document.execCommand('copy');
                    showFeedback();
                } catch (err2) {
                    console.warn('Copy failed', err2);
                    alert('Copy not supported in this browser. Select the link and copy manually.');
                }
            }
        });
    }

    function showFeedback() {
        if (!feedback) return;
        feedback.style.display = '';
        setTimeout(function () { feedback.style.display = 'none'; }, 3000);
    }

    // Share to social networks: repost first, then open
    const url = linkInput ? encodeURIComponent(linkInput.value) : encodeURIComponent(window.location.href);
    const shareMap = {
        twitter: () => {
            sendRepost('twitter');
            const text = encodeURIComponent(document.title);
            window.open(`https://twitter.com/intent/tweet?url=${url}&text=${text}`, '_blank', 'noopener');
        },
        telegram: () => {
            sendRepost('telegram');
            window.open(`https://t.me/share/url?url=${url}`, '_blank', 'noopener');
        },
        facebook: () => {
            sendRepost('facebook');
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`, '_blank', 'noopener');
        },
        whatsapp: () => {
            sendRepost('other');
            const base = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ? 'whatsapp://' : 'https://api.whatsapp.com';
            window.open(`${base}/send?text=${url}`, '_blank', 'noopener');
        }
    };

    const btnTwitter = document.getElementById('shareTwitter');
    const btnTelegram = document.getElementById('shareTelegram');
    const btnFacebook = document.getElementById('shareFacebook');
    const btnWhatsapp = document.getElementById('shareWhatsapp');

    if (btnTwitter) btnTwitter.addEventListener('click', shareMap.twitter);
    if (btnTelegram) btnTelegram.addEventListener('click', shareMap.telegram);
    if (btnFacebook) btnFacebook.addEventListener('click', shareMap.facebook);
    if (btnWhatsapp) btnWhatsapp.addEventListener('click', shareMap.whatsapp);

    if (modalEl) {
        modalEl.addEventListener('hide.bs.modal', () => {
            const active = document.activeElement;
            if (active && modalEl.contains(active)) {
                active.blur(); // 🔥 важно
            }
        });

        modalEl.addEventListener('hidden.bs.modal', () => {
            if (lastTrigger && typeof lastTrigger.focus === 'function') {
                try {
                    lastTrigger.focus({ preventScroll: true });
                } catch (err) {
                    try { lastTrigger.focus(); } catch (e2) { /* ignore */ }
                }
            }
        });
    }
});



// static/js/password-toggle.js
(function () {
    'use strict';

    function findToggles() {
        const toggles = Array.from(document.querySelectorAll('[data-password-toggle]'));
        Array.from(document.querySelectorAll('a, button')).forEach(el => {
            const txt = (el.textContent || '').trim();
            if (!el.hasAttribute('data-password-toggle') && txt === 'Show password') {
                el.setAttribute('data-password-toggle', '1');
                toggles.push(el);
            }
        });
        return Array.from(new Set(toggles));
    }

    function isPasswordInput(node) {
        return node && node.tagName.toLowerCase() === 'input' &&
            (node.type === 'password' || node.type === 'text' || node.dataset.isPassword === '1');
    }

    function isInsidePasswordToggle(toggle) {
        return toggle.classList.contains('password-toggle--inside');
    }

    function getPasswordFieldsForToggle(toggle) {
        const wrap = toggle.closest('.form-floating-password');
        if (wrap) {
            const inp = wrap.querySelector('input:not([type="hidden"])');
            if (inp && (inp.type === 'password' || inp.type === 'text')) {
                return [inp];
            }
            return [];
        }
        const form = toggle.closest('form');
        if (form) {
            return Array.from(form.querySelectorAll('input[type="password"], input[data-is-password="1"], input.password-field'));
        }
        return Array.from(document.querySelectorAll('input[type="password"], input[data-is-password="1"]'));
    }

    function updateToggleVisibility(toggle, fields) {
        const anyValue = fields.some(f => String(f.value || '').trim() !== '');
        const inside = isInsidePasswordToggle(toggle);

        if (inside) {
            if (anyValue) {
                toggle.classList.add('visible');
                toggle.setAttribute('aria-hidden', 'false');
                const shown = toggle.dataset.state === 'shown';
                toggle.innerHTML = shown
                    ? '<i class="fa fa-eye-slash" aria-hidden="true"></i>'
                    : '<i class="fa fa-eye" aria-hidden="true"></i>';
                toggle.setAttribute('aria-label', shown ? 'Hide password' : 'Show password');
            } else {
                toggle.classList.remove('visible');
                toggle.setAttribute('aria-hidden', 'true');
                fields.forEach(f => {
                    if (f.dataset._pwShown === '1') {
                        try { f.type = 'password'; } catch (e) { }
                        f.dataset._pwShown = '0';
                    }
                });
                toggle.innerHTML = '<i class="fa fa-eye" aria-hidden="true"></i>';
                toggle.setAttribute('aria-label', 'Show password');
                toggle.setAttribute('aria-pressed', 'false');
                toggle.dataset.state = 'hidden';
            }
            return;
        }

        if (anyValue) {
            toggle.classList.add('visible');
            toggle.setAttribute('aria-hidden', 'false');
        } else {
            toggle.classList.remove('visible');
            toggle.setAttribute('aria-hidden', 'true');
            fields.forEach(f => {
                if (f.dataset._pwShown === '1') {
                    try { f.type = 'password'; } catch (e) { }
                    f.dataset._pwShown = '0';
                }
            });
            toggle.innerHTML = `Show<i class="fa fa-eye mx-1"></i>password`;
            toggle.setAttribute('aria-pressed', 'false');
            toggle.dataset.state = 'hidden';
        }
    }

    function togglePassword(toggle, fields) {
        const isShown = toggle.dataset.state === 'shown';
        const inside = isInsidePasswordToggle(toggle);

        if (isShown) {
            fields.forEach(f => {
                try { f.type = 'password'; } catch (e) { }
                f.dataset._pwShown = '0';
            });
            toggle.dataset.state = 'hidden';
            toggle.setAttribute('aria-pressed', 'false');
            if (inside) {
                toggle.innerHTML = '<i class="fa fa-eye" aria-hidden="true"></i>';
                toggle.setAttribute('aria-label', 'Show password');
            } else {
                toggle.innerHTML = `Show<i class="fa fa-eye mx-1"></i>password`;
            }
        } else {
            fields.forEach(f => {
                try { f.type = 'text'; } catch (e) { }
                f.dataset._pwShown = '1';
            });
            toggle.dataset.state = 'shown';
            toggle.setAttribute('aria-pressed', 'true');
            if (inside) {
                toggle.innerHTML = '<i class="fa fa-eye-slash" aria-hidden="true"></i>';
                toggle.setAttribute('aria-label', 'Hide password');
            } else {
                toggle.innerHTML = `Hide<i class="fa fa-eye-slash mx-1"></i>password`;
            }
        }
    }

    function wireToggle(toggle) {
        const fields = getPasswordFieldsForToggle(toggle);
        if (!fields.length) {
            toggle.classList.remove('visible');
            return;
        }

        toggle.dataset.state = 'hidden';
        toggle.setAttribute('aria-pressed', 'false');

        // Блокируем Enter/Space когда toggle в фокусе (чтобы не срабатывать через клавиатуру)
        toggle.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ' || e.keyCode === 13 || e.keyCode === 32) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });

        // Клик: разрешаем только реальный мышиный клик (event.detail > 0).
        // Игнорируем клавиатурные / программные активации (detail === 0).
        toggle.addEventListener('click', e => {
            // если это click с клавиатуры или программный click (detail === 0) — игнорируем
            // (реальные мышиные клики имеют detail >= 1)
            if (typeof e.detail === 'number' && e.detail === 0) {
                // предотвращаем переход по ссылке (#) и всплытие, но не выполняем toggle
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            e.preventDefault();
            togglePassword(toggle, fields);
        });

        fields.forEach(f => {
            if (!isPasswordInput(f)) f.dataset.isPassword = '1';

            ['input', 'keyup', 'change'].forEach(evt =>
                f.addEventListener(evt, () => updateToggleVisibility(toggle, fields), { passive: true })
            );
        });

        updateToggleVisibility(toggle, fields);
    }

    function initPasswordToggles() {
        findToggles().forEach(t => {
            if (!t.dataset._pwInit) {
                t.dataset._pwInit = '1';
                wireToggle(t);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initPasswordToggles();

        // несколько повторных инициализаций на случай динамики/генератора пароля
        setTimeout(initPasswordToggles, 400);
        setTimeout(initPasswordToggles, 1000);

        if ('MutationObserver' in window) {
            new MutationObserver(() => initPasswordToggles())
                .observe(document.body, { childList: true, subtree: true });
        }
    });

})();


//pre code block badge, ckeditor
(function () {
    'use strict';

    function normalizeLang(s) {
        if (!s) return '';
        s = String(s).trim().toLowerCase();
        // небольшие сокращения/замены
        s = s.replace(/^language-/, '').replace(/^lang-/, '');
        return s;
    }

    function labelFromClassOrData(codeEl) {
        // сначала dataset
        if (codeEl && codeEl.dataset && codeEl.dataset.language) return normalizeLang(codeEl.dataset.language);

        // затем класс like language-python or lang-python
        if (codeEl && codeEl.className) {
            var m = (codeEl.className || '').match(/(?:^|\s)(?:language|lang)-([a-z0-9_+-]+)/i);
            if (m) return normalizeLang(m[1]);
        }
        // if pre has data-language
        var pre = codeEl && codeEl.closest ? codeEl.closest('pre') : null;
        if (pre && pre.dataset && pre.dataset.language) return normalizeLang(pre.dataset.language);

        return '';
    }

    function makeBadge(lang) {
        var span = document.createElement('span');
        span.className = 'code-lang-badge ' + ('lang-' + lang);
        span.textContent = lang;
        return span;
    }

    function applyBadges() {
        document.querySelectorAll('pre').forEach(function (pre) {
            // try find code element inside
            var code = pre.querySelector('code');
            if (!code) return;

            var lang = labelFromClassOrData(code);
            if (!lang) return;

            // mark pre so CSS can add top padding
            pre.classList.add('has-code-lang');

            // prevent adding duplicate badge
            if (pre.querySelector('.code-lang-badge')) return;

            var badge = makeBadge(lang);
            // place badge inside pre
            pre.insertBefore(badge, pre.firstChild);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyBadges, { once: true });
    } else {
        applyBadges();
    }
})();




// // sticky header (disabled for now)
// (function () {
//     const header = document.querySelector('.header');
//     if (!header) return;
//
//     const userMenu = document.getElementById('userMenu');
//
//     let lastScrollY = window.scrollY;
//     let ticking = false;
//
//     // spacer
//     const spacer = document.createElement('div');
//     spacer.className = 'header-spacer';
//     header.after(spacer);
//
//     const headerHeight = header.getBoundingClientRect().height;
//     spacer.style.height = headerHeight + 'px';
//
//     const DELTA = 6;
//
//     function closeUserMenu() {
//         if (userMenu) {
//             userMenu.classList.remove('open');
//         }
//     }
//
//     function onScroll() {
//         const currentY = window.scrollY;
//         const diff = currentY - lastScrollY;
//
//         if (Math.abs(diff) > DELTA) {
//             if (diff > 0) {
//                 // ⬇️ скроллим вниз — header исчезает
//                 header.classList.add('header--hidden');
//
//                 // 🔥 ВАЖНО: закрываем меню
//                 closeUserMenu();
//             } else {
//                 // ⬆️ скроллим вверх — header появляется
//                 header.classList.remove('header--hidden');
//             }
//
//             lastScrollY = currentY;
//         }
//
//         ticking = false;
//     }
//
//     window.addEventListener('scroll', () => {
//         if (!ticking) {
//             requestAnimationFrame(onScroll);
//             ticking = true;
//         }
//     }, { passive: true });
// })();



// main page items
function renderReplyErrors(container, messages) {
    if (!container) return;
    container.innerHTML = '';

    const box = document.createElement('div');
    box.className = 'invalid-feedback d-block';

    if (Array.isArray(messages)) {
        box.textContent = messages.join(' ');
    } else {
        box.textContent = String(messages);
    }

    container.appendChild(box);
}

function initFilterCardsPagination() {
    const fcw = document.getElementById('filterCardsWrapper');
    if (fcw && fcw.dataset.pageType === 'search') {
        return;
    }

    const STEP = 20;

    const wrapper = document.getElementById('showMoreWrapper');
    if (!wrapper) return;

    const btn = document.getElementById('showMoreBtn');
    const counter = document.getElementById('shownCounter');
    if (!btn || !counter) return;

    const cardsContainer = document.getElementById('filterCardsWrapper');
    const items = cardsContainer
        ? Array.from(cardsContainer.querySelectorAll('.item-card'))
        : Array.from(document.querySelectorAll('.item-card'));

    if (!items.length) return;
    const total = items.length;
    let shown = 0;

    function update(withAnimation, fromIndex) {
        if (typeof withAnimation === 'undefined') withAnimation = false;
        if (typeof fromIndex === 'undefined') fromIndex = 0;
        items.forEach(function (item, index) {
            if (index < shown) {
                if (item.classList.contains('listing-hidden')) {
                    item.classList.remove('listing-hidden');
                    if (withAnimation && index >= fromIndex) {
                        item.classList.remove('listing-animate');
                        void item.offsetWidth;
                        item.classList.add('listing-animate');
                    }
                }
            } else {
                item.classList.add('listing-hidden');
                item.classList.remove('listing-animate');
            }
        });
        counter.textContent = shown + ' / ' + total;
        btn.style.display = shown >= total ? 'none' : '';
    }

    shown = Math.min(STEP, total);
    update(false);

    btn.onclick = function () {
        const prev = shown;
        shown = Math.min(shown + STEP, total);
        update(true, prev);
    };
}

window.initFilterCardsPagination = initFilterCardsPagination;
LB.initFilterCardsPagination = initFilterCardsPagination;

document.addEventListener('DOMContentLoaded', function () {
    initFilterCardsPagination();
});




// static/js/bottom_menu.js
(function () {
    'use strict';

    const menu = document.getElementById('bottomSideMenu');
    const overlay = document.getElementById('bottomMenuOverlay');
    const openBtn = document.getElementById('bottomBurgerBtn');
    const closeBtn = document.getElementById('bottomMenuClose');

    if (!menu || !overlay || !openBtn || !closeBtn) return;

    let isOpen = false;

    function syncThemeColorForChrome() {
        const m = document.getElementById('meta-theme-color');
        if (!m) return;
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        m.setAttribute('content', dark ? '#0d1117' : '#ffffff');
    }

    function openBottomMenu() {
        if (isOpen) return;
        isOpen = true;

        lockScroll();

        overlay.classList.remove('hidden');
        menu.classList.remove('hidden');
        requestAnimationFrame(() => {
            menu.classList.add('open');
        });

        menu.removeAttribute('inert');
        menu.setAttribute('aria-hidden', 'false');

        /* Safari: re-assert theme-color after the dim overlay paints so the status / chrome area matches the drawer. */
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                syncThemeColorForChrome();
            });
        });

        closeBtn.focus();
    }

    function closeBottomMenu() {
        if (!isOpen) return;
        isOpen = false;

        document.activeElement?.blur();
        menu.classList.remove('open');

        setTimeout(() => {
            menu.classList.add('hidden');
            overlay.classList.add('hidden');

            menu.setAttribute('aria-hidden', 'true');
            menu.setAttribute('inert', '');

            unlockScroll();
            syncThemeColorForChrome();
        }, 250);
    }

    // ===== EVENTS =====
    openBtn.addEventListener('click', openBottomMenu);
    closeBtn.addEventListener('click', closeBottomMenu);
    overlay.addEventListener('click', closeBottomMenu);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen) {
            e.preventDefault();
            closeBottomMenu();
        }
    });

})();


// static/js/bootstrap_modal_fix.js
(function () {
    'use strict';

    document.addEventListener('hide.bs.modal', function (event) {
        // 🔑 убрать фокус ДО aria-hidden
        const active = document.activeElement;
        if (active && event.target.contains(active)) {
            active.blur();
        }
    });

})();


// SPA-logout
// (function () {
//     const menu = document.getElementById('userMenu');
//     if (!menu) return;

//     const logoutBtn = menu.querySelector('.user-logout-btn');
//     if (!logoutBtn) return;

//     function getCSRF() {
//         return document.querySelector('[name=csrfmiddlewaretoken]')?.value
//             || document.cookie.match(/csrftoken=([^;]+)/)?.[1];
//     }

//     logoutBtn.addEventListener('click', async (e) => {
//         e.preventDefault();
//         e.stopPropagation();

//         const url = logoutBtn.dataset.logoutUrl;
//         if (!url) return;

//         logoutBtn.style.pointerEvents = 'none';

//         try {
//             const resp = await fetch(url, {
//                 method: 'POST',
//                 headers: {
//                     'X-CSRFToken': getCSRF(),
//                     'X-Requested-With': 'XMLHttpRequest',
//                     'Accept': 'application/json'
//                 }
//             });

//             const data = await resp.json();
//             if (!data?.success) return;

//             // ✅ 1. закрываем tooltip
//             menu.classList.remove('open');

//             // ✅ 2. заменяем user-menu на Login
//             menu.outerHTML = `
//                 <a href="/profile/login/"
//                    class="text-muted text-decoration-none">
//                    <i class="fa fa-user-circle fs-4"></i>
//                 </a>
//             `;

//         } catch (err) {
//             console.error('Logout failed:', err);
//         }
//     });
// })();